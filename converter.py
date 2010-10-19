import sys
from xml.dom.minidom import Document, CDATASection
from xml.dom import minidom

def pts2xml(ptsFile, xmlFile=None):
	if xmlFile == None:
		xmlFile = ptsFile[:-4] + ".xml"
	
	f = open(ptsFile, 'r')
	fileContent = f.read().split()
	start =  fileContent.index("{") + 1
	end = fileContent.index("}")
	pts = []
	while start < end:
		pts.append((float(fileContent[start]),float(fileContent[start+1])))
		start += 2
	f.close()
		
	doc = Document()

	annotation = doc.createElement("annotation")
	doc.appendChild(annotation)

	objects = doc.createElement("objects")
	objects.setAttribute("type", "points")
	objects.setAttribute("count", "%.0f" % len(pts))
	annotation.appendChild(objects)

	text = ""
	for (x,y) in pts:
		text += "%.0f %.0f\n" % (x,y)
	cDataSection = doc.createCDATASection(text)
	objects.appendChild(cDataSection)

	objects = doc.createElement("objects")
	objects.setAttribute("type", "rectangles")
	objects.setAttribute("count", "int")
	annotation.appendChild(objects)
	
	cDataSection = doc.createCDATASection("\n")
	objects.appendChild(cDataSection)

	xml = open(xmlFile, 'w')
	xml.write(doc.toprettyxml(indent="  ", encoding="UTF-8"))
	xml.close()
	
def xml2pts(xmlFile, ptsFile=None):
	if ptsFile == None:
		ptsFile = xmlFile[:-4] + ".pts"
	
	xmldoc = minidom.parse(xmlFile)
	objects = xmldoc.getElementsByTagName("objects")
	
	pts = []
	rects = []
	
	for object in objects:
		lines = object.childNodes[1].data.splitlines()
		if object.attributes["type"].value == "points":
			for line in lines:
				pts.append(line.split(' '))
		elif object.attributes["type"].value == "rectangles":
			for line in lines:
				rects.append(line.split(' '))
	
	text = "version: 1\nn_points: %.0f\n{\n" % len(pts)
	for (x,y) in pts:
		text += "    %s %s\n" % (x,y)
	
	text += "}"
		
	f = open(ptsFile, 'w')
	f.write(text)
	f.close

if __name__ == "__main__":
    if len(sys.argv) == 4:
		
		(operation,input,output) = (sys.argv[1],sys.argv[2],sys.argv[3])
		
		if operation == "pts2xml":
			pts2xml(input,output)
		
		elif operation == "xml2pts":
			xml2pts(input,output)