import os,shutil
import face_recognition
import argparse
import sys
import json
from tqdm import tqdm
import dbhelper
import validatefacev2
import numpy
import extractfacev2
from pathlib import Path

EXTRACTEDFOLDER = "extractedFolder/"
if not os.path.exists(EXTRACTEDFOLDER):
    os.makedirs(EXTRACTEDFOLDER) 

RESULTFILE = "result.txt"

def listAllImage(folder):
    imageFiles = []
    for x in Path(folder).iterdir():
        if x.is_file():
            imageFiles.append(str(x))
        
    return imageFiles

def writeToFile(fileName,outputData):
    with open(fileName, "w") as outputFile:
        json_object = json.dumps(outputData, indent=4)
        outputFile.write(json_object)


def findByStudentId(array,id):
    for a in array:
        if "studentId" not in a:
            return None
        if a["studentId"] == id:
            return a
    return None



def classifyImage(imageFolders, dbString, dbName,dbModelCollection,dbResultCollection):
    db=dbhelper.connect(dbString,dbName)
    trainedModel = db[dbModelCollection].find()

    name = []
    knownEncoded = []
    for i in trainedModel:
        name.append(i["name"])
        knownEncoded.append(numpy.array(i["data"]))

    for folder in imageFolders:
        postId = os.path.basename(os.path.dirname(folder))
        imageFiles = listAllImage(folder)
        classifyOutput =[]
        for filePath in tqdm(imageFiles):
            extractfacev2.hogDetectFaces(str(filePath),EXTRACTEDFOLDER)
            
            for face in os.listdir(EXTRACTEDFOLDER):
                facePath = EXTRACTEDFOLDER  + face
                image = face_recognition.load_image_file(facePath)
                faceLocations = face_recognition.face_locations(image, model="hog")
                faceEncodings = face_recognition.face_encodings(image, faceLocations)

                if len(faceEncodings)!=0:
                    results = face_recognition.compare_faces(knownEncoded , faceEncodings[0],0.28)
                    for studentId,isMatch in zip(name, results):
                        if isMatch:
                            studentData = findByStudentId(classifyOutput,studentId)
                            if not studentData:
                                classifyOutput.append({"studentId":studentId,"images" :[str(filePath)]})
                            else:
                                studentData["images"] = list(set(studentData["images"] + [str(filePath)]))
                os.remove(facePath)
        print(classifyOutput)
        db[dbResultCollection].insert_one({"postId":postId,"studentPhotos":classifyOutput})

    

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--Folder", nargs='+', help="Image folders(end with '/')", required=True)
    parser.add_argument("-s", "--DBString", help="DB connection string", required=True)
    parser.add_argument("-n", "--DBName", help="DB name", default="face_rec")
    parser.add_argument("-mc", "--DBModelCol", help="DB model collection", default="model")
    parser.add_argument("-rc", "--DBResultCol", help="DB result collection", default="StudentImages")
    args = parser.parse_args()
    classifyImage(args.Folder, args.DBString, args.DBName, args.DBModelCol, args.DBResultCol)
   