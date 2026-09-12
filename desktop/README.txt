DELEGATUM — DESKTOP APPLICATION (Windows)
==========================================

🌍 Other languages: Français → LISEZ-MOI.txt · Deutsch → LIESMICH.txt ·
   Lëtzebuergesch → LIES-MICH.txt

Manage your staff delegation (Luxembourg) on YOUR own computer.
No server, no online account, no connection required: your data never leaves
the machine.

INSTALLATION (2 minutes, no installer)
--------------------------------------
1. Unzip the « Delegatum-Windows » folder wherever you want
   (for example: Documents\Delegatum). Avoid « Program Files », Windows
   blocks data writing there.
2. Double-click « Delegatum.exe ».

   First launch: Windows may display « Windows protected your PC »
   (SmartScreen — normal for an unsigned application). Click
   « More info » then « Run anyway ».

   Windows Defender may also flag a Trojan: this is a known FALSE POSITIVE
   for unsigned applications. Click the alert → « Actions » →
   « Allow on device ».

3. The Delegatum window opens on the « Create a staff delegation » screen
   (first launch only).

FIRST STEPS
-----------
On first launch, create your delegation:
   - organisation name, company headcount;
   - the chairperson's details: this first account is the administrator.

Afterwards: « 🔑 I already have access » to log in. Other members join with an
invitation code you hand out (« ✉️ Create access »).

YOUR DATA
---------
Everything lives in the « data » folder, next to Delegatum.exe:
   - delegatum.db   : the database (members, meetings, minutes, elections,
                      hours …);
   - .secret_key    : local signing key — do not share it;
   - emails\        : prepared notifications (.eml files to send).

Backup = copy this « data » folder to a USB stick or external drive from time
to time. Restore = put the folder back in place.

PRIVACY
-------
Nothing is sent to the Internet. Minutes are encrypted inside the application
(AES-256-GCM) with a vault password: even the files in the « data » folder do
not contain them in clear text. Keep the vault recovery key
(« Settings ») somewhere safe.

CLOSING
-------
Close the window (the cross). The application stops — no background service.

TROUBLESHOOTING
---------------
- « Windows protected your PC »: normal (unsigned application), see step 2.
- The window does not open: check that your antivirus is not blocking
  Delegatum.exe, then relaunch.
- Start over: close the application and delete the « data » folder
  (⚠️ everything is erased — make a backup first if needed).
- Moving to another computer: copy the « data » folder next to the new
  Delegatum.exe.

⚠️ Experimental application — provided for demonstration purposes only. It
does not constitute legal advice and is not guaranteed to comply with
Luxembourg legislation. For any labour law question, consult a qualified
professional or the Chambre des Salariés (CSL).

MIT License — source code: github.com/LostInTheBugs/Delegatum
