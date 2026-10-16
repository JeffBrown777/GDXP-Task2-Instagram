GDXP TASK 2 - FREE INSTAGRAM AUTOMATION - DIRECT INSTAGRAM LOGIN CORRECTION

PURPOSE
- No paid social-media scheduler.
- One approved PNG at 9:00 AM PHX.
- One approved PNG at 3:00 PM PHX.
- No invented caption.
- Duplicate suppression by exact PHX lane.
- Instagram media ID/permalink/timestamp receipt recorded only after verified publication.

FREE ROUTE
Instagram API with Instagram Login + GitHub Actions.

TARGET
Instagram: jeffbrown3579

REPOSITORY
JeffBrown777/GDXP-Task2-Instagram

CORRECTED AUTHORIZATION PATH
1. Target account must be an Instagram Professional account (Business or Creator).
2. Use Instagram Login, not the Facebook-Page traversal path.
3. Required Instagram permission scopes:
   instagram_business_basic
   instagram_business_content_publish
4. The Instagram access token is stored only as the GitHub Actions secret IG_ACCESS_TOKEN.
5. The publisher resolves the authenticated Instagram account ID at runtime and verifies the authenticated username is exactly jeffbrown3579 before any publish action.
6. Wrong account, missing token, duplicate lane, unverified PNG, API error, or missing receipt = HOLD.
7. Publication PASS requires media ID + permalink + timestamp + IMAGE receipt.

REPOSITORY SECRET
IG_ACCESS_TOKEN

NO LONGER REQUIRED
IG_USER_ID is not required as a GitHub secret; the authenticated account ID is resolved from Instagram at runtime.

NON-SECRET EXECUTION VALUES
IG_IMAGE_BASE_URL
  https://raw.githubusercontent.com/JeffBrown777/GDXP-Task2-Instagram/main/png
IG_API_VERSION
  v24.0
IG_GRAPH_HOST
  https://graph.instagram.com
IG_EXPECTED_USERNAME
  jeffbrown3579

GDXP TASK 2
9:00 AM PHX -> one PNG
3:00 PM PHX -> one PNG
NO VERIFIED PUBLICATION RECEIPT = NO SUCCESS CLAIM.
