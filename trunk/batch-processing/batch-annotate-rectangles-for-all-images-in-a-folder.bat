set haarcascade=files\haarcascade_frontalface_alt2.xml
set python_script=files\detect_face.py

set input_folder=test-images\
set image_extension=.png
set rectange_extension=.rect

for /f %%a IN ('dir /b %input_folder%*%image_extension%') do python %python_script% %haarcascade% %input_folder%%%~na%image_extension% %input_folder%%%~na%rectange_extension%

for /f %%a IN ('dir /b %input_folder%*%image_extension%') do python ..\converter.py rect2xml %input_folder%%%~na%rectange_extension% %input_folder%%%~na.xml

for /f %%a IN ('dir /b %input_folder%*%image_extension%') do del %input_folder%%%~na%rectange_extension%

pause