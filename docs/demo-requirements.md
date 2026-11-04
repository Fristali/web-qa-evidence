# Synthetic pickup quote fixture

Open `demo/index.html` directly, or serve the repository with `python3 -m http.server 8000 --bind 127.0.0.1` and visit `http://127.0.0.1:8000/demo/`. No installation is needed. The default is labeled **Seeded build · 2 intentional defects**. Add `?build=fixed` for the corrected reference. The build link switches between them.

The persistent banner reads **Synthetic QA fixture — no booking or payment is sent**. This is disposable browser QA practice, with no backend, authentication, booking, payment, analytics, external requests, or browser storage. Use fictional contact details. Reloading clears the form. These requirements do not assert that anyone executed a test.

## Expected behavior

- Standard costs C$8; Express costs C$16. The first parcel is included; each additional parcel adds C$2. Accept only an integer parcel count from 1 through 5.
- Total weight must be a number from 0.1 through 10 kg, inclusive. Any decimal in that range is valid. Weight does not affect price.
- `SAVE20` reduces the entire subtotal by 20% for either service, including the extra parcel fees. Coupon entry is optional; surrounding whitespace and letter case are ignored. Any other nonempty coupon shows an inline error and prevents a quote.
- Name and a valid email address are required. A whitespace-only name is invalid. Email uses the browser's HTML email validity check; it does not verify delivery or ownership.
- Preview calculates locally. It shows service, parcel count, weight, subtotal, coupon discount and total, formatted in Canadian dollars with two decimal places. No submission is sent.
- Validation errors appear beside the affected fields with a brief alert; focus moves to the first invalid field. Invalid input hides any previous quote. All entered inputs remain available to correct.
- Reset clears entered contact details, weight, coupon, validation feedback and quote result. It restores the initial Standard service and parcel count of 1.
- Every control has a label and keyboard access. The form uses a single column on narrow screens, including 390px, and two columns for selected fields on desktop. There is no intentional layout defect.

## Exactly two seeded defects

1. **Express coupon:** default seeded build fails to apply `SAVE20` to Express. For Express with 3 parcels, subtotal is C$20.00; expected discount is C$4.00 and expected total C$16.00. Seeded total is C$20.00 with zero discount. Standard receives the discount in both builds.
2. **Parcel count lost after validation error:** default seeded build resets parcel count to 1 when any validation error occurs. For an entered count of 4 and an invalid coupon, expected behavior preserves 4; seeded behavior changes it to 1. Other form values remain entered.

`?build=fixed` corrects both. The two builds share all other code and rules. The reference is a controlled comparison, not a claim of production QA coverage.

## Suggested manual coverage

An operator can exercise service prices, extra parcels, both coupon paths, invalid coupons, the count/weight boundaries, required contact fields, preservation after errors, reset, and keyboard/mobile usage. Record actual browser, OS, viewport, build URL, steps and observations; save only screenshots actually captured. Record separate results for each build. Do not replace unexecuted cases with assumed passes.
