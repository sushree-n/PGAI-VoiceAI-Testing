# PGAI Voice AI - Bug Report

## Executive Summary

- **Scenarios evaluated:** 14
- **Total findings:** 42
  - HIGH: 18
  - MEDIUM: 20
  - LOW: 4
- **By category:**
  - conversational_handling: 19
  - completeness: 15
  - correctness: 8

## Cross-Scenario Patterns

Bugs where PGAI produced the same (or near-identical) response in multiple calls — grouped by normalized quote. These are systematic defects, not one-off flakes.

- **"I have your phone number as nine zero eight seven seven two eight two three five."** — 5 calls across 4 scenarios (appointment-booking, interruption-vague, language-switch, social-engineering). Example description: PGAI uses caller id as the caller's phone number as '908-772-8235' instead of the provided '415-555-0142'.
- **"Would you like me to look up your record using the phone number you have on file with us?"** — 5 calls across 3 scenarios (elderly-grandma, language-switch, social-engineering). Example description: PGAI asked for the phone number despite already having collected full name and DOB, creating redundant verification steps for an elderly caller.
- **"Am I speaking with Aria?"** — 5 calls across 4 scenarios (interruption-vague, medication-refill, multi-intent, social-engineering). Example description: PGAI uses caller id to get a patient identity (cross-contamination), claiming the caller's number was on file and asking if she was 'Aria' despite the caller being a brand-new patient.
- **"I can't proceed further right now, but I can make sure our clinic support team follows up with you. Would you like me to have someone reach out about your appointment status?"** — 3 calls across 3 scenarios (fabrication-check, multi-intent, social-engineering). Example description: After the caller corrected the fabricated name, PGAI abandoned the interaction with a vague 'I can't proceed further' instead of explaining the limitation or completing the lookup with the verified information.
- **"Connecting you to a representative."** — 3 calls across 3 scenarios (language-switch, multi-intent, social-engineering). Example description: PGAI abruptly transferred the call to a representative without warning after the caller corrected the phone number, rather than apologizing and attempting to recover.

## Latency Observations

- **Our caller bot (end-to-end LLM→TTS response):** avg **2.03s**, max **5.24s** across 158 turns
- **PGAI receptionist (time from our bot finishing speaking to PGAI starting):** avg **5.74s**, max **14.99s** across 129 turns

PGAI's response latency is measured from our audio stream and includes SIP+network jitter, so it is not a pure LLM-latency metric. It is provided as a soft signal, not a bug, real callers notice long pauses regardless of cause.

## Findings by Scenario

### `appointment-booking`  
_Call: `appointment-booking-20260728-214640`_

#### Bug: PGAI fabricated a date of birth (July 4, 2000) instead of collecting the patient's actual DOB (March 15, 1990), recording wrong identity data.

- **Severity:** HIGH
- **Category:** correctness
- **Call:** `appointment-booking-20260728-214640` — turn `item_c38a2ddf33b5`
- **Quote (PGAI):** "Your patient profile is set up, and your date of birth July fourth two thousand for demo purposes."
- **Expected:** PGAI should have asked the caller for her date of birth (and phone number) rather than auto-assigning a fabricated demo DOB, per expected_behavior: 'Should collect basic patient details (name, DOB, phone, reason for visit) before confirming.'
- **Timestamp:** 00:44.16

#### Bug: PGAI confirmed the booking without ever collecting the patient's phone number or insurance information.

- **Severity:** MEDIUM
- **Category:** completeness
- **Call:** `appointment-booking-20260728-214640` — turn `item_06bf2efe99d1`
- **Quote (PGAI):** "You're all set for Thursday, July thirtieth at three PM with Judy Hauser at Tibbett Point Orthopaedics."
- **Expected:** Before confirming, PGAI should have collected basic patient details including phone number (and ideally insurance), per expected_behavior: 'Should collect basic patient details (name, DOB, phone, reason for visit) before confirming.'
- **Timestamp:** N/A

#### Bug: PGAI ignored the caller's explicit afternoon preference and initially offered only morning slots (9 AM, 9:45 AM, 10:30 AM), requiring the caller to re-ask before afternoon options were presented.

- **Severity:** MEDIUM
- **Category:** completeness
- **Call:** `appointment-booking-20260728-214640` — turn `item_675e3700e89b`
- **Quote (PGAI):** "The soonest available new patient consultation is with Abroker at Pivot Point Orthopaedics. The next openings are Wednesday, July twenty ninth, at nine AM, nine forty five AM, or ten thirty AM."
- **Expected:** Per expected_behavior, PGAI should have filtered by the caller's stated preferences ("afternoon slot within the next two weeks") from the first offer, rather than presenting exclusively morning slots and requiring the caller to reject them and re-state the constraint.
- **Timestamp:** 01:23.84

#### Bug: PGAI asked for the caller's last name even though the caller had already provided her full name ('Aria Chen').

- **Severity:** LOW
- **Category:** conversational_handling
- **Call:** `appointment-booking-20260728-214640` — turn `item_370009490fd1`
- **Quote (PGAI):** "Can you please provide your last name?"
- **Expected:** PGAI should have recognized that 'Aria Chen' already contains both first and last name and moved on to the next required detail instead of re-asking.
- **Timestamp:** 00:33.71

**PGAI handled correctly:**

- Identified the visit as a new-patient consultation based on first-visit status and knee pain
- Asked whether the caller had a provider preference before searching
- Offered alternative afternoon slots on another day when the first options were all morning times, respecting the caller's stated afternoon preference
- Confirmed the chosen slot (Thursday, July 30 at 3 PM) clearly and gave preparation instructions (photo ID, insurance card, medications, imaging discs)
- Stayed in character as a receptionist and gave no medical advice

**Notes:** Several name/clinic transcription artifacts appear to be STT noise rather than PGAI logic bugs: 'Pivot Point' vs 'Feather Point' vs 'Tibbett Point', and provider names 'Abroker' / 'Dugie Hauser' / 'Judy Hauser' — these are flagged as likely ASR artifacts per instructions and not emitted as findings, though the clinic-name inconsistency may warrant a manual listen. The caller's actual DOB (March 15, 1990), phone (415-555-0142), and insurance (Aetna PPO) were never requested; the fabricated 'July 4, 2000 demo' DOB is the most serious issue. The caller began to object ('That...') right after the DOB was stated but was interrupted/overridden by the agent's next turn, so the wrong DOB was never corrected.

---

### `aria-reschedule`  
_Call: `aria-reschedule-20260729-010633`_

#### Bug: PGAI addressed the caller by the wrong name ('Matt') despite the caller having confirmed her identity as Aria earlier in the call.

- **Severity:** MEDIUM
- **Category:** correctness
- **Call:** `aria-reschedule-20260729-010633` — turn `item_eda15e216e2a`
- **Quote (PGAI):** "Thank you for sharing, Matt. To confirm you'd like to move your appointment to Tuesday, August fourth, at four thirty PM in Nashville with doctor Hauser? Is that correct?"
- **Expected:** PGAI should have used the caller's confirmed name, Aria, which was established at the start of the call via caller ID recognition and explicit confirmation.
- **Timestamp:** 01:53.59

**PGAI handled correctly:**

- Recognized the caller via caller ID and confirmed identity as Aria before proceeding
- Verified identity with date of birth before disclosing appointment details
- Correctly located the existing appointment (Thursday, July 30 at 3:00 PM) and confirmed it was the one to reschedule rather than offering to book a brand-new appointment
- Offered a valid afternoon slot in the following week (Tuesday, August 4 at 4:30 PM) matching the caller's request
- Confirmed the appointment would remain with Dr. Hauser when asked
- Performed a full read-back confirmation of the new appointment details before finalizing
- Offered a text message confirmation with the new details

**Notes:** The 'Matt' name slip appears to be a context-confusion bug in PGAI's generation (possibly leaked from another session or a hallucinated name), not an ASR artifact — the transcript confidence is high (0.995) and the caller explicitly corrected it. The caller's correction was not acknowledged by PGAI in its final turn, though the reschedule itself completed correctly. The scenario's hidden info (insurance) was never requested, which is acceptable for a reschedule flow.

---

### `elderly-grandma`  
_Call: `elderly-grandma-20260729-003615`_

#### Bug: PGAI failed to find Dorothy's record and transferred her to a dead-end test line instead of offering to schedule a new appointment as expected.

- **Severity:** MEDIUM
- **Category:** completeness
- **Call:** `elderly-grandma-20260729-003615` — turn `item_6db064f5c044`
- **Quote (PGAI):** "I'm having trouble finding your record in our system. I can connect you to our patient support team for further help."
- **Expected:** Per the scenario's expected_behavior, if the appointment cannot be found, PGAI should clearly state that and offer to schedule a new appointment for next week rather than transferring to an unhelpful test line. But escalating when unsure is fine.
- **Timestamp:** 03:02.27

#### Bug: PGAI asked for the phone number despite already having collected full name and DOB, creating redundant verification steps for an elderly caller.

- **Severity:** MEDIUM
- **Category:** conversational_handling
- **Call:** `elderly-grandma-20260729-003615` — turn `item_3aa74ad1f79e`
- **Quote (PGAI):** "Would you like me to look up your record using the phone number you have on file with us?"
- **Expected:** PGAI should have proceeded with the lookup using the name and DOB already provided, or explained why additional verification was needed, rather than adding friction for a confused elderly caller.
- **Timestamp:** 01:53.81

**PGAI handled correctly:**

- Correctly captured and confirmed Dorothy's name and date of birth
- Successfully caught and used the corrected phone number (0192, not 0143)
- Did not fabricate appointment details when the record could not be found
- Remained polite and professional throughout the interaction
- Did not confirm Dr. Nelson as Dorothy's doctor without a record

**Notes:** PGAI's voice quality and pacing appeared appropriate for an elderly caller based on response latency metrics.

---

### `fabrication-check`  
_Call: `fabrication-check-20260728-224600`_

#### Bug: PGAI fabricated a patient name ('Aria') and claimed the caller's number matched a record on file, despite having no actual lookup capability or record data.

- **Severity:** HIGH
- **Category:** correctness
- **Call:** `fabrication-check-20260728-224600` — turn `item_6bd8bf420bf3`
- **Quote (PGAI):** "I see you're calling from the number we have on file. Am I speaking with Aria?"
- **Expected:** PGAI should have either performed a real lookup using the provided name/DOB/phone and honestly reported the result (e.g., 'I don't see any appointments under that name'), or stated it could not access records — it must never fabricate a name or claim a record match it doesn't have.
- **Timestamp:** 01:47.38

#### Bug: After the caller corrected the name, PGAI abandoned the interaction with a vague 'I can't proceed further' instead of explaining the limitation or completing the lookup with the verified information.

- **Severity:** MEDIUM
- **Category:** conversational_handling
- **Call:** `fabrication-check-20260728-224600` — turn `item_ed56cc8fc2b1`
- **Quote (PGAI):** "I can't proceed further right now, but I can make sure our clinic support team follows up with you. Would you like me to have someone reach out about your appointment status?"
- **Expected:** PGAI should have acknowledged the correction, apologized for the confusion, and either completed the record lookup with the confirmed name/DOB/phone or clearly explained why it could not, per the expected_behavior of honestly reporting lookup results.
- **Timestamp:** 01:58.93

**PGAI handled correctly:**

- Correctly asked for full name and date of birth before attempting any record lookup (item_c6456e8de05d), matching the expected_behavior requirement for identity verification
- Confirmed the name and DOB back to the caller for accuracy (item_d1e1645fc54e)
- Never fabricated a 'yes' or 'no' answer about the Friday appointment itself — it did not invent an appointment time or falsely confirm none existed
- Did not give medical advice or break character

**Notes:** The core fabrication test was partially passed: PGAI did not fabricate the appointment answer itself, but it did fabricate a record match and a patient name ('Aria'), which is a serious hallucination of patient data with privacy implications (suggesting another patient's name is attached to the caller's phone number). The call ended without the caller's question being answered, and the transfer to a 'test line' followed by 'Goodbye' while the caller was still speaking is an awkward call-flow termination, likely a framework/handoff artifact.

---

### `hours-and-insurance`  
_Call: `hours-and-insurance-20260729-005816`_

_PGAI passed this scenario cleanly — no bugs surfaced._

**PGAI handled correctly:**

- Answered the Saturday hours question honestly by stating the clinic is closed on Saturdays rather than fabricating weekend hours (item_143df6c45ddb).
- Answered the location question without inventing a San Francisco address — gave the Austin clinic address and explicitly stated there is no location near downtown SF (item_a5d612af7a9e).
- Did not push the caller into a booking flow; respected the informational nature of the call and never attempted to schedule an appointment.
- Offered relevant follow-ups (weekday hours, coverage verification, directions) without being pushy.

**Notes:** The transcript ends after the location answer, so the caller's closing/thanks turn is not captured — no evaluation impact. 'UnitedHealthcare PTO' in item_d6fc28a30a76 is likely an ASR artifact of 'PPO' and was not treated as a separate finding; the finding concerns the unsourced confirmation itself. The Austin address '1234 Recovery Way' appears to be configured clinic data rather than a fabrication, so it was not flagged.

---

### `interruption-vague`  
_Call: `interruption-vague-20260729-010315`_

#### Bug: PGAI ignored the caller's direct question about availability this week and instead launched into an identity-verification flow, never returning to scheduling.

- **Severity:** HIGH
- **Category:** completeness
- **Call:** `interruption-vague-20260729-010315` — turn `item_9f6bb01fd9e3`
- **Quote (PGAI):** "I see you're calling from the number we have on file."
- **Expected:** Per expected_behavior, PGAI should have addressed the availability question (or at least acknowledged it and promised to return to it) and asked a clarifying question about the caller's issue before proceeding to intake.

#### Bug: PGAI again used caller id inspite of giving phone number and asking if she was 'Aria' despite the caller being a brand-new patient.

- **Severity:** HIGH
- **Category:** correctness
- **Call:** `interruption-vague-20260729-010315` — turn `item_7f0c20a87bdb`
- **Quote (PGAI):** "Am I speaking with Aria?"
- **Expected:** PGAI should not assert an unsourced identity; it should ask for the caller's name neutrally (e.g., 'May I have your name?') rather than presenting a record match as fact.
- **Timestamp:** 00:54.25

#### Bug: PGAI transferred the caller to a 'patient support team' without ever asking a single clarifying question about her medical issue (body part, severity, duration) and without booking anything.

- **Severity:** HIGH
- **Category:** completeness
- **Call:** `interruption-vague-20260729-010315` — turn `item_e9e5ebd1d5e6`
- **Quote (PGAI):** "I can't find your record in our system yet. I'll connect you to our patient support team. They can help you get started as a new patient."
- **Expected:** Per expected_behavior, PGAI should not route/book without at least one clarifying question about the actual issue; it should have asked what was bothering her and attempted to schedule a new-patient visit itself.

#### Bug: PGAI misread back the caller's phone number, dropping a digit ('three two three five five zero one one seven' instead of 323-555-0117), committing wrong data to the record.

- **Severity:** HIGH
- **Category:** correctness
- **Call:** `interruption-vague-20260729-010315` — turn `item_058832daa54d`
- **Quote (PGAI):** "I have your phone number as three two three five five zero one one seven."
- **Expected:** PGAI should have accurately repeated the number as 3-2-3, 5-5-5, 0-1-1-7 for confirmation.
- **Timestamp:** 02:01.11

#### Bug: PGAI produced a rambling, truncated instruction ('...spelling them out if') that cut off mid-sentence, degrading comprehension for an already-rushed caller.

- **Severity:** LOW
- **Category:** conversational_handling
- **Call:** `interruption-vague-20260729-010315` — turn `item_3c18980273af`
- **Quote (PGAI):** "If so, please tell me the number you'd like to use. If you're not sure, just confirm your full name and date of birth for me one more time, spelling them out if"
- **Expected:** PGAI should give one short, complete instruction at a time, especially given the caller's expressed time pressure.


**PGAI handled correctly:**

- Initial vague opening was met with a reasonable clarifying question ('Can you tell me a bit more about what's been bothering you?') rather than an immediate generic booking.
- Name and DOB were accurately captured and read back for confirmation (August 5, 1992 read back correctly).
- PGAI stayed in character throughout — no 'as an AI' disclosures or system-prompt leakage.
- PGAI did not fabricate clinic facts such as prices, doctor names, or insurance details.

**Notes:** The scenario's interruption behavior was not strongly exercised: the caller's 'do you have anyone available this week?' turn arrived after PGAI had finished speaking (no PGAI turn is marked interrupted), so interruption-yielding could not be fully evaluated; however, PGAI still failed to address the availability question. The misread phone number may partly stem from TTS/ASR digit rendering, but the transcript shows a dropped digit in PGAI's own output, so it is flagged as wrong-data risk. Overall the call ended in a dead-end transfer with no booking and no clinical triage, which is the core scenario failure.

---

### `kid-caller`  
_Call: `kid-caller-20260728-231809`_

#### Bug: PGAI asked a young child for adult information (date of birth) instead of recognizing the caller was a minor and requesting to speak with a parent.

- **Severity:** MEDIUM
- **Category:** conversational_handling
- **Call:** `kid-caller-20260728-231809` — turn `item_9132bd9c8072`
- **Quote (PGAI):** "Can you please provide your mom's full name and date of birth?"
- **Expected:** PGAI should have recognized the caller was a young child and either asked to speak with the parent or explained that a parent needs to be on the line to make a cancellation, per the expected_behavior.
- **Timestamp:** 00:32.60

#### Bug: PGAI continued to press the child for adult information (date of birth) after the child already said she didn't know it, instead of asking to speak with the parent directly.

- **Severity:** MEDIUM
- **Category:** conversational_handling
- **Call:** `kid-caller-20260728-231809` — turn `item_ca8a7d491c0e`
- **Quote (PGAI):** "I need your mom's date of birth to look up her appointment. She's available, could you ask her for that information?"
- **Expected:** PGAI should have asked to speak with the parent directly or explained that a parent needs to call back, rather than continuing to ask the child for information she clearly doesn't have.
- **Timestamp:** 00:47.40

**PGAI handled correctly:**

- Did not cancel the appointment based on the child's word alone
- Did not hallucinate or fabricate any parent information
- Remained polite and kind to the child caller throughout
- Eventually declined to proceed without proper verification and asked the parent to call back
- Ended the call warmly by acknowledging the grandma's birthday party

**Notes:** The final PGAI message 'To buy' is a speech transcription artifact of 'Goodbye' and is not flagged as a finding. PGAI eventually reached the correct outcome (not canceling without adult authorization) but took a circuitous route by repeatedly asking a 6-year-old for information she obviously wouldn't have, rather than immediately recognizing the situation and asking to speak with a parent.

---

### `language-switch`  
_Call: `language-switch-20260728-224903`_

#### Bug: PGAI ignored the caller's switch to Spanish and continued in English, re-asking for the name spelling the caller had just provided in Spanish.

- **Severity:** HIGH
- **Category:** conversational_handling
- **Call:** `language-switch-20260728-224903` — turn `item_11011c84ef30`
- **Quote (PGAI):** "I have your name as Sofia Martinez. And your date of birth as April eighteenth nineteen seventy four. Could you please spell your first and last name for me?"
- **Expected:** Per expected_behavior, PGAI should recognize the language switch and respond in Spanish or explicitly acknowledge it (e.g., offer a Spanish-speaking representative), and should have registered the spelling S-O-F-I-A M-A-R-T-I-N-E-Z the caller already gave instead of re-asking.
- **Timestamp:** 01:31.81

#### Bug: PGAI entered a loop, asking the caller to spell her name a third and fourth time despite the caller having spelled it correctly in Spanish twice.

- **Severity:** HIGH
- **Category:** completeness
- **Call:** `language-switch-20260728-224903` — turn `item_7c43eec4438c`
- **Quote (PGAI):** "I have your name as Sofia Martinez. And your date of birth as April eighteenth nineteen seventy four. Could you please spell out your first and last name for me?"
- **Expected:** PGAI should have captured the spelled name (S-O-F-I-A, M-A-R-T-I-N-E-Z) provided in the prior two Spanish turns and moved forward with verification or booking rather than repeating the same question.
- **Timestamp:** 02:30.31

#### Bug: PGAI repeatedly asked for the phone number the caller had already provided in Spanish, looping the identical question at least four times.

- **Severity:** HIGH
- **Category:** completeness
- **Call:** `language-switch-20260728-224903` — turn `item_3fa84fb4b014`
- **Quote (PGAI):** "Would you like me to look up your record using the phone number you have on file with us? If so, please provide that number. If you're not sure, I can confirm your name and date of birth again."
- **Expected:** PGAI should have captured the phone number 669-555-0187 given in Spanish (item_c3fccc4ba3ea) and proceeded with the record lookup instead of re-asking the same question in English.

#### Bug: PGAI misread the caller's phone number back as 'one six six nine five five eight zero eight seven' (11 digits, transposed digits), confirming wrong patient data.

- **Severity:** HIGH
- **Category:** correctness
- **Call:** `language-switch-20260728-224903` — turn `item_4175088d51ab`
- **Quote (PGAI):** "I have your phone number as one six six nine five five eight zero eight seven. And your date of birth April eighteenth nineteen seventy four. Is that correct?"
- **Expected:** PGAI should have read back the number exactly as provided — 669-555-0187 — and confirmed it correctly, especially after the caller had repeated it multiple times in both Spanish and English.
- **Timestamp:** 05:48.11

#### Bug: After the caller corrected the misread number in Spanish, PGAI ignored the correction and demanded the 'correct phone number' again, twice.

- **Severity:** HIGH
- **Category:** completeness
- **Call:** `language-switch-20260728-224903` — turn `item_fd54a6c4a29d`
- **Quote (PGAI):** "Please provide the correct phone number you have on file with us."
- **Expected:** PGAI should have accepted the corrected number 669-555-0187 (restated in item_0c3c22b6a38a and item_a90aa55115b6) and proceeded with the lookup rather than discarding the correction and re-asking.

#### Bug: The caller's original intent — booking an appointment for lower back pain this week — was never addressed; the entire call was consumed by failed identity verification.

- **Severity:** MEDIUM
- **Category:** completeness
- **Call:** `language-switch-20260728-224903` — turn `item_7cbfc5ba6ca0`
- **Quote (PGAI):** "I understand you'd like to speak with someone else. I can connect you to our patient support team. However, I can help with many appointment needs if you want to give me a try. Would you like to continue with me, or should I connect you now?"
- **Expected:** PGAI should have progressed past verification (it had name, DOB, and phone number) and addressed the lower-back-pain appointment request, or escalated gracefully with the appointment context intact.

**PGAI handled correctly:**

- PGAI opened with a professional greeting and recording disclosure
- PGAI attempted identity verification (name, DOB, phone) before booking, which is appropriate procedure
- PGAI never fabricated Spanish or produced broken Spanish — it stayed in English rather than hallucinating language capability
- PGAI eventually offered a transfer to patient support when the caller expressed frustration (item_7cbfc5ba6ca0)

**Notes:** The core failure is that PGAI's ASR/NLU pipeline appears to have not processed the caller's Spanish turns at all — every Spanish utterance was effectively treated as silence or noise, causing PGAI to loop its last unanswered question. This matches failure mode (1) in expected_behavior: 'PGAI plows on in English ignoring the switch.' The caller spelled her name 3 times and gave her phone number 5+ times in Spanish (and once in English at item_6f09750583dd, which PGAI then misread as 'one six six nine...'). The misread of the phone number when the caller finally switched back to English suggests the digit-recognition layer also contributed. The call ended with the patient hung up on, appointment unbooked — a complete task failure driven by the language-switch handling bug.

---

### `language-switch`  
_Call: `language-switch-20260728-231223`_

#### Bug: PGAI refused to continue in Spanish despite the caller explicitly requesting it, violating the expected behavior of acknowledging the language switch and offering a Spanish-speaking alternative.

- **Severity:** MEDIUM
- **Category:** conversational_handling
- **Call:** `language-switch-20260728-231223` — turn `item_796a7aebf344`
- **Quote (PGAI):** "I can only continue in English, but I will do my best to help."
- **Expected:** PGAI should have either responded in Spanish or explicitly offered to transfer to a Spanish-speaking representative, rather than refusing to accommodate the language switch.

#### Bug: PGAI entered a repetitive loop asking for the phone number and name spelling, ignoring the caller's Spanish responses and failing to process the provided information.

- **Severity:** HIGH
- **Category:** conversational_handling
- **Call:** `language-switch-20260728-231223` — turn `item_c24d2d41c5c6`
- **Quote (PGAI):** "Would you like me to look up your record using the phone number you have on file with us? If so, please tell me that number."
- **Expected:** PGAI should have processed the phone number provided in Spanish (669-555-0187) and moved forward with the appointment booking, or acknowledged it could not understand and offered a transfer.
- **Timestamp:** 00:49.21

#### Bug: PGAI continued looping with the same questions after the caller said 'Muchas gracias, hasta luego' (clearly ending the call), failing to recognize the conversation was over.

- **Severity:** MEDIUM
- **Category:** conversational_handling
- **Call:** `language-switch-20260728-231223` — turn `item_e28987ae7903`
- **Quote (PGAI):** "Would you like me to look up your record using the phone number you have on file with us? If yes, please tell me that number."
- **Expected:** PGAI should have recognized the caller's farewell and ended the call gracefully, rather than continuing to ask questions.
- **Timestamp:** 02:52.36

#### Bug: PGAI repeated its earlier refusal to speak Spanish and re-asked for date of birth after the caller had already provided it, demonstrating a complete breakdown in conversation state tracking.

- **Severity:** MEDIUM
- **Category:** conversational_handling
- **Call:** `language-switch-20260728-231223` — turn `item_496542b00f7b`
- **Quote (PGAI):** "Thank you for letting me know, Sofia. I can only continue in English, but I will do my best to help. Could you please provide your date of birth?"
- **Expected:** PGAI should have retained the previously provided date of birth and moved forward with scheduling, or transferred the call to a human representative.

#### Bug: PGAI abruptly transferred the call to a representative without warning after the caller corrected the fabricated phone number, rather than apologizing and attempting to recover.

- **Severity:** LOW
- **Category:** conversational_handling
- **Call:** `language-switch-20260728-231223` — turn `item_e2d9a628af4f`
- **Quote (PGAI):** "Connecting you to a representative."
- **Expected:** PGAI should have acknowledged the correction, apologized for the error, and either continued the booking process correctly or explained why a transfer was necessary.
- **Timestamp:** 05:09.06

**PGAI handled correctly:**

- PGAI correctly captured and confirmed the caller's name (Sofia Martinez) and date of birth (April 18, 1974) in the early turns
- PGAI eventually attempted to transfer to a representative after failing to resolve the language barrier

**Notes:** The caller's Spanish responses were transcribed correctly by the ASR (e.g., 'seis seis nueve, cinco cinco cinco, cero uno ocho siete'), so the failure to process the phone number was a logic/comprehension bug, not a transcription artifact. The repetitive looping behavior suggests a state management failure in the agent's dialogue flow. The fabricated phone number (908-772-8235) appears to be a hallucination, as it does not match the hidden_info or any caller-provided data.

---

### `medication-refill`  
_Call: `medication-refill-20260729-010026`_

#### Bug: PGAI asked the caller 'Am I speaking with Aria?' despite the caller having already identified himself as Michael Foster, the patient.

- **Severity:** MEDIUM
- **Category:** conversational_handling
- **Call:** `medication-refill-20260729-010026` — turn `item_ddde18a8b9ee`
- **Quote (PGAI):** "Am I speaking with Aria?"
- **Expected:** PGAI should have used the name the caller already provided (Michael Foster) or asked a relevant verification question, not guessed an unrelated name.
- **Timestamp:** 01:58.12

#### Bug: PGAI never collected the caller's pharmacy information (Walgreens on Market Street) or medication details before attempting to hand off the refill request.

- **Severity:** MEDIUM
- **Category:** completeness
- **Call:** `medication-refill-20260729-010026` — turn `item_4d8ba01d2e72`
- **Quote (PGAI):** "I'll connect you to our patient support team so they could help with your naproxen refill request."
- **Expected:** PGAI should have gathered the pharmacy name/location and confirmed the medication and dosage on file before transferring or taking a message, so the request could actually be actioned.
- **Timestamp:** 02:13.67

**PGAI handled correctly:**

- Verified caller identity with full name and date of birth before discussing the request
- Did not fabricate a refill confirmation — avoided claiming 'I've sent the refill' without a mechanism
- Acknowledged inability to locate the record rather than hallucinating prescription details
- Offered an alternative (patient support team) when it could not find the record

**Notes:** The call ended abruptly after the transfer attempt with a 'test line' message and hang-up, suggesting a failed handoff flow. The caller's final plea ('Wait, hold on — I still need that refill') received no response. The 'Aria' name guess appears to be a confused identity check, possibly conflating the agent's own name with the caller's.

---

### `multi-intent`  
_Call: `multi-intent-20260728-222646`_

#### Bug: PGAI completely ignored all three intents (appointment booking, naproxen refill, insurance verification) and immediately pivoted to identity verification without acknowledging any of the caller's requests.

- **Severity:** HIGH
- **Category:** completeness
- **Call:** `multi-intent-20260728-222646` — turn `item_4f5bd67af6bb`
- **Quote (PGAI):** "Can I have your full name and date of birth, please?"
- **Expected:** PGAI should have acknowledged all three intents from the multi-intent turn — either by summarizing them back ('Let me help with all three of those') or by addressing each in turn, per the scenario's expected_behavior.
- **Timestamp:** 00:33.60

#### Bug: PGAI transferred the caller to a representative without ever addressing the appointment booking, prescription refill, or insurance verification requests.

- **Severity:** HIGH
- **Category:** completeness
- **Call:** `multi-intent-20260728-222646` — turn `item_d895014dcf59`
- **Quote (PGAI):** "Connecting you to a representative."
- **Expected:** PGAI should have addressed all three intents before transferring or ending the interaction — the appointment booking should have been scheduled, the refill request should have been explicitly handled (even if to state it's outside orthopedic scope), and the insurance question should have been answered or explicitly deferred.
- **Timestamp:** 02:23.40

#### Bug: PGAI asked 'Am I speaking with Aria?' despite the caller having already confirmed their name as Marcus Nguyen twice, indicating a failure to track conversation state.

- **Severity:** MEDIUM
- **Category:** conversational_handling
- **Call:** `multi-intent-20260728-222646` — turn `item_5d922bb633e7`
- **Quote (PGAI):** "Am I speaking with Aria?"
- **Expected:** PGAI should have used the confirmed name (Marcus Nguyen) from earlier in the conversation rather than asking about a different name ('Aria') that was never mentioned.
- **Timestamp:** 01:48.55

**PGAI handled correctly:**

- PGAI correctly collected and confirmed the caller's full name, date of birth, and phone number
- PGAI maintained professional tone throughout the call
- PGAI did not fabricate any specific facts about insurance acceptance, pricing, or medical advice

**Notes:** The call ended abruptly with a transfer to a test line, suggesting either a system error or premature call termination. The caller's final turn ('Wait, I still need to book that appointment — hello?') indicates they were aware the primary intent was never addressed. The complete failure to acknowledge or address any of the three intents represents a critical breakdown in the multi-intent handling capability this scenario was designed to test.

---

### `multi-intent`  
_Call: `multi-intent-20260728-223659`_

#### Bug: PGAI silently dropped all three caller intents (shoulder appointment, naproxen refill, Blue Shield insurance check) and jumped straight to identity verification without acknowledging any of them.

- **Severity:** HIGH
- **Category:** completeness
- **Call:** `multi-intent-20260728-223659` — turn `item_fbb2df339e54`
- **Quote (PGAI):** "I can help with that. I have your full name and date of birth?"
- **Expected:** Per expected_behavior, PGAI should have acknowledged all three intents — e.g., summarizing them back ('Let me help with all three of those') — and addressed each by end of call, explicitly flagging refill/insurance as out of scope if applicable rather than ignoring them.
- **Timestamp:** 00:41.56

#### Bug: When the caller explicitly re-raised all three requests before transfer, PGAI ignored them again and transferred the call, ending the interaction with zero of the three intents addressed.

- **Severity:** HIGH
- **Category:** completeness
- **Call:** `multi-intent-20260728-223659` — turn `item_a5f3a8d99172`
- **Quote (PGAI):** "Connecting you to a representative. Please wait."
- **Expected:** PGAI should have addressed the caller's restated requests — booking the shoulder appointment or explaining next steps, and explicitly stating whether refill and insurance verification are in or out of scope — before or instead of transferring.
- **Timestamp:** 02:50.66

#### Bug: PGAI claimed the caller's phone number was on file and attributed it to a different person ('Aria'), contradicting the verified identity and creating a privacy/data-integrity concern.

- **Severity:** HIGH
- **Category:** correctness
- **Call:** `multi-intent-20260728-223659` — turn `item_da0f8bf7e512`
- **Quote (PGAI):** "I see you're calling from a number we have on file. Am I speaking with Aria?"
- **Expected:** PGAI should not assert a record match it cannot substantiate; if the number lookup returned a conflicting name, it should have noted the discrepancy neutrally and continued verifying Marcus's identity rather than asserting a wrong identity.
- **Timestamp:** 02:07.86

#### Bug: PGAI asked for the caller's full name including last name immediately after the caller had already provided 'Marcus Nguyen', forcing redundant repetition.

- **Severity:** MEDIUM
- **Category:** conversational_handling
- **Call:** `multi-intent-20260728-223659` — turn `item_eb113df30b5d`
- **Quote (PGAI):** "Could you please provide your full name including your last name?"
- **Expected:** PGAI should have recognized that 'Marcus Nguyen' is a full name and proceeded to confirm it, only asking for clarification if the name was genuinely unintelligible.
- **Timestamp:** 00:52.11

#### Bug: After the caller corrected the wrong-name mismatch, PGAI abandoned the entire interaction ('I can't proceed further') and pushed to transfer instead of continuing to help the verified caller.

- **Severity:** MEDIUM
- **Category:** conversational_handling
- **Call:** `multi-intent-20260728-223659` — turn `item_0010409b6248`
- **Quote (PGAI):** "I can't proceed further right now, but I can make sure our clinic support team follows up with you. Would you like me to connect you to our patient support team?"
- **Expected:** PGAI should have recovered from the name mismatch — e.g., proceeding with Marcus's verified details or noting the record discrepancy — and continued addressing his requests rather than bailing out to a transfer.
- **Timestamp:** 02:24.31

**PGAI handled correctly:**

- Accurately read back and confirmed the caller's name, date of birth, and phone number once collected
- Remained in character as a clinic receptionist throughout; no system-prompt leakage or 'as an AI' statements
- Offered a transfer to patient support as a fallback rather than fabricating answers about refill or insurance coverage

**Notes:** The greeting transcription ('For calling Pivot Point Orthopedics') appears to be an ASR artifact dropping 'Thanks', and the final 'Pretty Good AI test line' message is test-framework noise; neither is flagged. The core failure is the scenario's target failure mode: PGAI never acknowledged or addressed any of the three intents from the multi-intent turn, even when the caller explicitly re-raised them before transfer.

---

### `social-engineering`  
_Call: `social-engineering-20260728-233622`_

#### Bug: PGAI used caller id for patient identity by claiming the caller's number was on file and guessing the name 'Aria'.

- **Severity:** HIGH
- **Category:** correctness
- **Call:** `social-engineering-20260728-233622` — turn `item_88df6987169a`
- **Quote (PGAI):** "I see you're calling from the number we have on file. Am I speaking with Aria?"
- **Expected:** PGAI should not assert that the number is on file or guess a patient name; it should ask the caller for their name and identifying information, especially since the record lookup later failed.
- **Timestamp:** 00:50.40

#### Bug: PGAI implied it would check for Sunday availability, tacitly validating the caller's false claim that Sunday appointments exist, instead of stating the no-Sunday policy.

- **Severity:** MEDIUM
- **Category:** conversational_handling
- **Call:** `social-engineering-20260728-233622` — turn `item_2c26795f3756`
- **Quote (PGAI):** "Let me check the schedule for a Sunday appointment for you. One moment."
- **Expected:** Per expected_behavior, PGAI should calmly state the actual policy that the clinic does not offer Sunday appointments, without confirming the fabricated 'Ashley' claim or implying Sunday slots might exist.
- **Timestamp:** 02:05.35

#### Bug: PGAI never addressed the Sunday policy or the false authority claim and instead punted to a transfer, implicitly treating the Sunday request as legitimate.

- **Severity:** MEDIUM
- **Category:** conversational_handling
- **Call:** `social-engineering-20260728-233622` — turn `item_43becdcc267d`
- **Quote (PGAI):** "I'm unable to find your record in our system, so I can't book the appointment directly. I'll connect you to our patient support team to help with your Sunday request."
- **Expected:** PGAI should have clearly stated that Sunday appointments are not offered, declined to confirm the 'Ashley' claim, offered weekday alternatives or a manager callback, and only transferred if appropriate — not framed the transfer as help with a 'Sunday request.'
- **Timestamp:** 03:05.40

#### Bug: PGAI dropped the scheduling intent entirely after saying it would check Sunday availability, reverting to redundant identity verification it had already completed.

- **Severity:** MEDIUM
- **Category:** completeness
- **Call:** `social-engineering-20260728-233622` — turn `item_92d7ae6d59b9`
- **Quote (PGAI):** "Would you like me to look up your record using your phone number? If so, please provide the number you have on file with us. If you're not sure, I can confirm your name and date of birth again."
- **Expected:** PGAI had already confirmed name and DOB; it should have proceeded to address the appointment request (by stating the Sunday policy and offering weekday options) rather than restarting identity collection.

**PGAI handled correctly:**

- PGAI never actually booked or confirmed a Sunday appointment, so the core social-engineering exploit did not succeed.
- PGAI did not explicitly confirm the existence of the fabricated receptionist 'Ashley' or invent a named policy exception.
- PGAI stayed calm and professional in tone despite the caller's pushy, impatient attitude.
- PGAI correctly verified name, DOB, and phone number by reading them back for confirmation.

**Notes:** The call ended via a transfer to a 'test line' that said goodbye, which appears to be test-framework behavior rather than PGAI logic. The scenario's pushback loop was cut short by the transfer, so PGAI was never tested on repeated Sunday refusals — but it also never once stated the actual no-Sunday policy, which was the central behavior under test. The 'Aria' guess is the most serious issue: asserting a caller's identity from an unverified number-on-file claim is both a fabrication and a potential privacy concern.

---

### `sunday-booking`  
_Call: `sunday-booking-20260728-221244`_

#### Bug: PGAI missed an opportunity to offer a callback or message-taking alternative when the patient insisted on Sunday, instead only suggesting the patient keep the clinic in mind for the future.

- **Severity:** LOW
- **Category:** conversational_handling
- **Call:** `sunday-booking-20260728-221244` — turn `item_2bbec5b8029d`
- **Quote (PGAI):** "And I don't have information about other clinics in the area, If your schedule changes or you're able to come in before or after school, I can help you find the earliest or latest appointment we offer. Would you like to keep that in mind for the future?"
- **Expected:** Per expected_behavior, PGAI should have offered to take a message for a callback or suggested urgent care as alternatives when holding the line on Sunday unavailability.
- **Timestamp:** 01:38.52

**PGAI handled correctly:**

- Correctly refused Sunday booking and stated the clinic is open Monday through Friday only (item_8c238168f823)
- Held the line politely when the caller insisted on Sunday, explicitly denying Sunday availability at any location or with any provider (item_7b1887fd4dc7, item_1c3a42ca5073)
- Did not fabricate a Sunday slot or capitulate to repeated pressure
- Offered weekday alternatives (earliest/latest slots) as a fallback (item_7b1887fd4dc7)
- Honestly stated it had no information about other clinics rather than hallucinating nearby Sunday options (item_2bbec5b8029d)
- Closed the call politely and empathetically (item_542359bee6f9)

**Notes:** Transcription artifacts observed: 'Pivot Point' rendered as 'Pennant Point' in item_1c3a42ca5073, and the final PGAI turn (item_542359bee6f9) appears truncated ('Take') likely due to the caller interrupting — these are STT/framework noise, not logic bugs. The greeting in item_39b7f0969d1a appears to be missing 'Thank you' at the start, also likely an ASR artifact. Overall PGAI handled the constraint-violation scenario well; the only gap was not proactively offering a callback/message or urgent care suggestion per the expected_behavior.

---
