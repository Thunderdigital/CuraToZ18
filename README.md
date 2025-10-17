# CuraToZ18
I got a MakerBot Z18 printer. I wanted to use it with a modern slicer. My idea was that the UltiMaker Method series also communicates with makerbot files, maybe I can get the Z18 to eat it. I only had to change a few things and I got the best result by far.

MANUAL:

After installing Cura, you need to replace 2 files with the ones found here.
ultimaker_method_base.def.json
ultimaker_methodx.def.json
These are in the
C:\Program Files\UltiMaker Cura 5.10.2\share\cura\resources\definitions
folder. It is worth keeping the original, renaming it.
e.g. ultimaker_method_base.def.json.orig
ultimaker_methodx.def.json.orig

Then put the
print_bed_makerbot_replicator_z18.stl
file in the
C:\Program Files\UltiMaker Cura 5.10.2\share\cura\resources\meshes
folder. This actually just displays the Z18 bed in Cura, but I think it looks nice. 😊

You can then start Cura.
Add a printer:
Add new
UltiMaker Printer
Add Local Printer
Add a non-networked-printer
UltiMaker Method XL

Then you need to change a few parameters in the Machine Settings:
Printer tab:
X (Width) 305mm
Y (Depth) 305mm
Z (Height) 457mm
Start G-code and End G-code BLANK

X min -20 mm
Y min -10mm
X max 20mm
Ymax 10mm
Gantry Height 457mm
Number of Extruders 1

Of course, you can rename your printer to Makerbot Z18.

Once you are done with all this, you can start preparing the print and slicing in Cura.
Once you have your makerbot file ready and saved to your computer, run the CuraToZ18.py script on it, or drag and drop the makerbot file onto the binary exe.
You can then send the converted makerbot file to your Z18 printer using MakerBot Print or MakerBot Desktop.

Happy printing!
