DELEGATUM — DESKTOP APPLICATION (macOS)
=======================================

🌍 Other languages: Français → LISEZ-MOI.txt · Deutsch → LIESMICH.txt ·
   Lëtzebuergesch → LIES-MICH.txt

Manage your staff delegation (Luxembourg) on YOUR own computer.
No server, no online account, no connection required: your data never leaves
the machine.

INSTALLATION (2 minutes, no installer)
--------------------------------------
1. Unzip « Delegatum-macOS.zip » wherever you want (for example: Documents).
   Keep everything as-is: your data will live next to the application.
2. Double-click « Delegatum.app ».

   First launch: macOS may display "macOS cannot verify the developer of
   this application" (normal for an unsigned application). Right-click
   « Delegatum.app » → « Open », then confirm « Open ». Afterwards, a
   double-click is enough.

3. The Delegatum window opens on the « Create a staff delegation » screen
   (first launch only).

FIRST STEPS
-----------
On first launch, create your delegation:
   - organisation name, company headcount;
   - the chairperson's details: this first account is the administrator.

Afterwards: « 🔑 I already have access » to log in. Other members join with an
invitation code you hand out (« ✉️ Create access »).

HEALTH & SAFETY REGISTER & ITM FILE
-----------------------------------
The health & safety delegate records findings (Art. L.414-14). The register
is tamper-evident: every action is chained by fingerprint, and an entry is
never deleted — it is voided, with a reason. From the « S&S register » page:
   - « 📄 ITM file (PDF + integrity JSON) »: the printable PDF and the
     integrity dossier to hand to the Labour and Mines Inspectorate;
   - « 📊 CSV export »: the full list (active and voided);
   - « 🔐 Seal now » (board): timestamps the register fingerprint and
     prepares a copy of the seal by email.
An integrity dossier can be re-checked at any time from « 🔍 Verify an
integrity file » (bottom of every page).

YOUR DATA
---------
Everything lives in the « data » folder, next to Delegatum.app:
   - delegatum.db   : the database (members, meetings, minutes, elections,
                      hours …);
   - .secret_key    : local signing key — do not share it;
   - emails/        : prepared notifications (.eml files to send).

Backup = copy this « data » folder to a USB stick or external drive from time
to time. Restore = put the folder back in place.
Tip: if you move Delegatum.app, take the « data » folder with it.

PRIVACY
-------
Nothing is sent to the Internet. Minutes are encrypted inside the application
(AES-256-GCM) with a vault password: even the files in the « data » folder do
not contain them in clear text. Keep the vault recovery key
(« Settings ») somewhere safe.

CLOSING
-------
Close the window (the red button). The application stops — no background
service.

TROUBLESHOOTING
---------------
- "macOS cannot verify the developer": see step 2 (right-click → Open).
  Only once.
- The window does not open: launch the application again; if the problem
  persists, the « error.log » file next to the application contains
  details to send to the developer.
- The « data » folder does not appear next to the application (protected
  location): Finder → « Go » menu → « Go to Folder… » →
  ~/Library/Application Support/Delegatum
- Start over: close the application and delete the « data » folder
  (⚠️ everything is erased — make a backup first if needed).
- Moving to another computer: copy the « data » folder next to the new
  application.
- Update: download the new archive and replace « Delegatum.app » (keep your
  « data » folder).

⚠️ Experimental application — provided for demonstration purposes only. It
does not constitute legal advice and is not guaranteed to comply with
Luxembourg legislation. For any labour law question, consult a qualified
professional or the Chambre des Salariés (CSL).

MIT License — source code: github.com/LostInTheBugs/Delegatum
