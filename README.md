GDXP TASK 2 - FREE INSTAGRAM AUTOMATION - CORRECTED

PURPOSE
- No paid social-media scheduler.
- One approved PNG at 9:00 AM PHX.
- One approved PNG at 3:00 PM PHX.
- No invented caption.
- Duplicate suppression by slot.
- Instagram media ID/permalink receipt recorded only after verified publication.

FREE ROUTE
Meta/Instagram publishing API + GitHub Actions.

TARGET
Instagram: jeffbrown 3579

REPOSITORY
JeffBrown777/GDXP-Task2-Instagram

CURRENT REQUIREMENTS
1. Instagram target must be a Professional account (Business or Creator) with content-publishing permission.
2. A Meta app/token must authorize content publishing.
3. GitHub repository holds this workflow and the approved PNG posting queue.
4. The PNG URLs must be reachable by Meta over HTTPS.
5. Secrets are stored in GitHub Actions secrets, never in source files.

REPOSITORY SECRETS
IG_USER_ID
IG_ACCESS_TOKEN

REPOSITORY VARIABLES
IG_IMAGE_BASE_URL
  https://raw.githubusercontent.com/JeffBrown777/GDXP-Task2-Instagram/main/png
IG_API_VERSION
  v24.0
IG_GRAPH_HOST
  https://graph.facebook.com

GDXP TASK 2
9:00 AM PHX -> one PNG
3:00 PM PHX -> one PNG
NO VERIFIED PUBLICATION RECEIPT = NO SUCCESS CLAIM.
