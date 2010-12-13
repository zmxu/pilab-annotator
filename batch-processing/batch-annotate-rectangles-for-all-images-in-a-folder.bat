set haarcascade=files\haarcascade_frontalface_alt2.xml
set python_script=files\detect_face.py

set input_folder=test-images\
set image_extension=.jpg
set rectange_extension=.rect

for /f %%a IN ('dir /b %input_folder%*%image_extension%') do python %python_script% %haarcascade% %input_folder%%%~na%image_extension% %input_folder%%%~na%rectange_extension%

pause