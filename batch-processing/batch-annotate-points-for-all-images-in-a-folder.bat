REM echo off
set haarcascade=files\haarcascade_frontalface_alt2.xml
set model=files\ismail.amf
set shape_model=files\ismail.xml
set fit=files\fit_facial_points.exe

set input_folder=test-images\
set image_extension=.jpg
set point_extension=.pts


for /f %%a IN ('dir /b %input_folder%*%image_extension%') do %fit% -m %model% -s %shape_model% -h %haarcascade% -i %input_folder%%%~na%image_extension% -S %input_folder%%%~na%point_extension% -g 0 -n 24

for /f %%a IN ('dir /b %input_folder%*%image_extension%') do python ..\converter.py pts2xml %input_folder%%%~na%point_extension% %input_folder%%%~na.xml

for /f %%a IN ('dir /b %input_folder%*%image_extension%') do del %input_folder%%%~na%point_extension%


pause