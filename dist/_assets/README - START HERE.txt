DOCUMENT DE-IDENTIFIER  -  Portable edition
============================================

WHAT THIS IS
  A tool that removes people and counterparty names from documents before you
  send them to an AI, and puts the real names back into the AI's answer.
  Everything runs on YOUR computer. Nothing is sent to the internet.

WHAT YOU NEED
  Nothing. Python and all components are included in this folder.
  No installation, no admin rights required.


HOW TO USE IT
-------------
1. Copy this whole folder somewhere on your PC
   (for example, your Documents folder).
   Tip: it runs a little faster from a local folder than from inside a
   synced OneDrive/SharePoint folder, but either works.

2. Double-click  "Launch De-identifier.bat"

3. A black window opens, then a browser tab appears showing the app.
   (If the tab doesn't open by itself, open your browser and go to:
    http://localhost:8731 )

4. When you're finished, close the black window to stop the app.


FIRST TIME?  THE MOST IMPORTANT STEP
------------------------------------
Go to the "Entity dictionary" tab and add your real people and counterparties
(with their short forms / aliases). This list is what makes the tool reliable.
You can paste a whole list at once under "Bulk import".


GOOD TO KNOW
------------
- Your saved dictionary ("entities.json") and the encrypted re-identification
  vault ("vault" folder) are created inside this folder as you use it.
- KEEP YOUR PASSPHRASE. If you lose it, that job's names cannot be recovered.
- Keep the Job ID together with each de-identified document - you need both the
  Job ID and the passphrase to put the real names back.
- Windows may show a "Windows protected your PC" message the first time. Click
  "More info" then "Run anyway". (It appears because the launcher isn't signed.)


TROUBLE?
--------
- If the browser shows an error at first, wait a few seconds and refresh -
  the app may still be starting.
- If port 8731 is busy, close any other copy of the app and try again.
- If nothing happens, your IT security software may be blocking it - contact
  whoever gave you this folder.
