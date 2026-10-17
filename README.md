# GDXP TASK 2 — INSTAGRAM

## PURPOSE

Task 2 publishes one approved image in each contracted Phoenix lane:

- 09:00 PHX
- 15:00 PHX

Target Instagram account: `jeffbrown3579`

Route: Instagram API with Instagram Login + GitHub Actions.

No caption, hashtags, or other creative text are added.

## CONTROLLING EXECUTION CONTRACT

`task2_contract.json` locks:

- route: `instagram_login`
- Graph host: `https://graph.instagram.com`
- API version: `v24.0`
- target username: `jeffbrown3579`
- timezone: `America/Phoenix`
- exact 09/15 PHX schedules
- exact approved queue order

Any contract mismatch fails closed before publication.

## AUTHORIZATION

GitHub Actions secret:

`IG_ACCESS_TOKEN`

The workflow requires the token before lane, artifact, or publication work.

The authenticated Instagram profile must resolve to:

- username exactly `jeffbrown3579`
- a numeric Instagram user ID
- account type `BUSINESS` or `MEDIA_CREATOR`

The runtime publishing quota endpoint must also pass before publication.

## APPROVED ASSETS

Source identity is controlled by `approved_source_assets.json`.

`bootstrap_assets.py`:

1. Reconstructs each approved PNG from the repository's encoded source chunks.
2. Verifies reconstructed bytes against the pinned source SHA-256.
3. Auto-replaces a missing or corrupted local PNG only with the verified source bytes.
4. Generates the JPEG API transport derivative with pinned Python dependencies.
5. Verifies the generated JPEG before release.

The approved PNG is the source artifact. The JPEG is transport only.

## IMMUTABLE PUBLIC MEDIA

The workflow validates source and transport artifacts, commits any materialized changes, then freezes the exact 40-character Git commit SHA.

Instagram receives media only from:

`https://raw.githubusercontent.com/JeffBrown777/GDXP-Task2-Instagram/<IMMUTABLE_COMMIT>/instagram_media/<ASSET>.jpg`

The public JPEG signature and SHA-256 must match the validated transport artifact before publication.

The receipt stores the immutable publication commit.

## PUBLICATION

The publisher:

1. Re-verifies the authenticated target.
2. Re-verifies publishing quota.
3. Validates the complete state history.
4. Suppresses a lane already represented by one live-verified Instagram receipt.
5. Creates the Instagram media container.
6. Polls container state once per minute, for no more than five checks.
7. Publishes only a `FINISHED` container.
8. Retrieves the published Instagram media receipt.
9. Requires numeric `media_id`, `IMAGE`, HTTPS Instagram permalink, timezone-qualified timestamp, and username `jeffbrown3579`.
10. Atomically writes verified state.

## RECEIPT / RELEASE

A Task 2 receipt contains:

- slot
- approved source filename
- approved source SHA-256
- JPEG transport filename
- JPEG transport SHA-256
- immutable publication commit
- Instagram `media_id`
- Instagram permalink
- Instagram timestamp
- Instagram username

The final workflow gate independently re-verifies:

- state integrity
- queue progression from the most recent receipt
- exact current lane receipt
- approved source identity
- historical immutable source bytes
- historical immutable transport bytes
- unique slot, media ID, and permalink
- live Instagram media ID
- live Instagram username
- live media type
- live permalink
- live timestamp
- Phoenix publication date

Only then may the workflow reach:

`TASK 2 PASS — VERIFIED INSTAGRAM PUBLICATION RECEIPT — CLOSE`

## GMAIL

Gmail is corroboration only. A GitHub notification, digest, or self-authored email is not an Instagram publication receipt and cannot create PASS/CLOSE.

## RELEASE RULE

GitHub success alone is not Task 2 success.

No verified Instagram publication receipt = no Task 2 PASS/CLOSE.
