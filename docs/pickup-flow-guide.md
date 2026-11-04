# Pickup quote fixture: user-flow handoff

This original client-only demonstration calculates a price preview. It sends no booking, payment or contact message and stores no information. Use fictional data such as Sample Tester and tester@example.com.

1. Start the local server using the README command and open `/demo/?build=fixed` for the corrected reference.
2. Enter a name and syntactically valid email, choose Standard or Express, enter 1–5 whole parcels and a total weight from 0.1 through 10 kg.
3. Optionally enter SAVE20. Choose **Preview quote**. Standard starts at C$8 and Express at C$16; each additional parcel adds C$2. SAVE20 discounts the entire subtotal by 20%.
4. Correct any highlighted field and preview again. The fixed reference retains the selected parcel count after an error.
5. Read subtotal, discount and total. **Reset form** clears entered name/email/weight/coupon, feedback and result; service returns to Standard and parcel count to 1. Reloading also clears the form.

For example, three Express parcels cost C$20 before the coupon and C$16 with SAVE20. The default seeded build intentionally omits this Express discount and clears parcel count on validation failure. Use it only to practice reproducing the documented defects.

For developers, the observed matrix and reproduction steps are in the sample report. Recheck C02 and C07 at both viewport sizes after changes, then run the remaining ten cases to catch connected regressions. Do not extrapolate these client-only results to backend delivery or production payment behavior.
