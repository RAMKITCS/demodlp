import os
import sys
import time
from ast import For

from clean import clean
from DBcode import mongoDB
from gcsconnect import (get_signed_url, get_signed_url2, read_file,
                        write_file,write_file_bucket2,move_blob,
                        delete_blob)

st=time.time()
#print(Predict("Classification/sport_3.txt"))
print(time.time()-st)

import shutil
from datetime import datetime as dt
from datetime import timedelta
from pathlib import Path

import uvicorn
from fastapi import (Body, Depends, FastAPI, File, Form, Request, UploadFile,
                     status)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (HTMLResponse, JSONResponse, PlainTextResponse,
                               RedirectResponse)
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_login import LoginManager
from werkzeug.utils import secure_filename

app=FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static/",StaticFiles(directory="app/static/"),name="static")
render_template=Jinja2Templates(directory="templates").TemplateResponse

class NotAuthenticatedException(Exception):
    pass
SECRET=os.urandom(24).hex()
manager = LoginManager(SECRET,token_url="/login",use_cookie=True,custom_exception=NotAuthenticatedException,default_expiry=timedelta(hours=1))
manager.cookie_name = "username"
@manager.user_loader()
def load_user(username:str):
    print("calling",__name__)
    return username
manager.useRequest(app)
@app.post("/model")
def hello(request:Request,path:str=Form(None),pythonfile:str=Form(),data:str=Form(None)):
    try:
        if path:
            sys.path.insert(1,path)
        pyfile=__import__(pythonfile)
        return pyfile.Predict(data)
    except Exception as e:
        print(str(e))
        return str(e)
@app.get("/login",response_class=HTMLResponse)
def login(request:Request):
    print("user",request.state.user)
    if request.state.user:
        return RedirectResponse('/index')
    return render_template("login.html",{'request':request})
@app.get('/logout')
def logout(request:Request):
    res=RedirectResponse("/login",status_code=status.HTTP_302_FOUND)
    manager.set_cookie(res,"")
    print("user-logout",request.state.user)
    return res
@app.post("/login")
def login(request:Request,form_data:OAuth2PasswordRequestForm = Depends()):
    #print(form_data.password)
    #print(form_data.username not in ["yt","test","demo"], (form_data.password!="tcs"))
    user=mongoDB.login_check(form_data.username,form_data.password)
    if not (user):
        print("raised")
        error="Invalid Credentials"
        return render_template('login.html',{'request':request,"error":error})
    access_token=manager.create_access_token(data={"sub":form_data.username})
    res=RedirectResponse(url="/index",status_code=status.HTTP_302_FOUND)
    manager.set_cookie(res,access_token)
    print(access_token,res)
    return res


@app.get("/upload")
def upload(request:Request,token=Depends(manager)):
    # fname=request.query_params.get('fname')
    # doc_name=request.query_params.get('doc_name')
    # if fname is not None and doc_name is not None :
    #     print(fname,doc_name)
    #     delete_blob("Classification_Input/"+doc_name+"."+fname)
    return render_template('file_upload.html',{'request':request})


@app.post("/upload")
def upload(request:Request,file:UploadFile=File(),doc_name:str=Form()):
        try:            
            filename=secure_filename(doc_name+"."+file.filename)           
            f= file.file.read()
            path="Classification_Input/"+filename                 
            write_file(path,f)
            sys.path.insert(1,"DlpClassify")
            print(path)
            
            print("POST")
            mongoDB.insert({"doc_id":doc_name,"name":filename,"upload_date":dt.utcnow().strftime(("%d/%m/%Y %H:%M:%S")),"queue":"Scan","doc_type":""})
            from main2 import call_pre
            call_pre(path)
            # if(filename):                
            #     return render_template("file_upload.html",{'request':request,"status":1,"fname":file.filename,"doc_name":doc_name})
            # else:
            #      return render_template("file_upload.html",{'request':request})

            return RedirectResponse("/index")
        except Exception as e:
            print(str(e))
            return str(e)
        
        
        
@app.post("/uploadproc")
def uploadproc(request:Request,fname:str=Form(),doc_name:str=Form()):
    filename=secure_filename(doc_name+"."+fname)        
    path="Classification_Input/"+filename
           
    try:        
        # move_blob(os.environ['bucket_name'],path,os.environ['bucket_name'],path) 
        mongoDB.insert({"doc_id":doc_name,"name":filename,"upload_date":dt.utcnow().strftime(("%d/%m/%Y %H:%M:%S")),"queue":"Scan","doc_type":""})
        return render_template("file_upload.html",{'request':request,"status":2})
    except Exception as e:
            print(str(e))
            return str(e)    
        
        
        
        
        
@app.get('/')
def home(request:Request):
    return RedirectResponse("/login")
@app.get('/index')
def home(request:Request,token=Depends(manager)):
    return render_template('dashboard.html',{"request":request})
@app.post('/index')
def home(request:Request,token=Depends(manager)):
    return render_template('dashboard.html',{"request":request})
@app.get('/getData')
def getData(request:Request):
    date=request.query_params['date']
    print("date",date)
    #print(mongoDB.findall_json('1'))
    return (mongoDB.findall_json(date))
@app.get("/fileInfo")
def fileInfo(date:str):
    #date=request.query_params['date']
    #print("date",date)
    #print(mongoDB.findall_json('1'))
    #output=mongoDB.Connection().count_documents({'upload_date':{'$regex':date},"queue":"Completed"})
    total_files=mongoDB.Connection().count_documents({})
    completed_count=mongoDB.Connection().count_documents({'completed_date':{'$regex':date}})
    return (total_files,completed_count)
@app.exception_handler(NotAuthenticatedException)
def authenticate_exception(request: Request, exc: NotAuthenticatedException):
    return RedirectResponse("/login")
@app.get('/getSignedurl')
def getSignedurl(request:Request):
    filename=request.query_params.get('filename')
    action = request.query_params.get('action')
    download_name = request.query_params.get('download_name')
    url=get_signed_url(filename,action,download_name)
    return JSONResponse(url)
@app.get('/getSignedurl2')
def getSignedurl2(request:Request):
    filename=request.query_params.get('filename')
    action = request.query_params.get('action')
    #download_name = request.query_params.get('download_name')
    url=get_signed_url2(filename,action)
    return JSONResponse(url)
@app.get('/getImageUrl')
def getImageUrls(request:Request,path:str):
    import json
    import time

    #from collections import defaultdict
    st=time.time()
    #from collections import defaultdict
    
    #path=request.query_params.get('path')
    print(path)
    # long-loop-386604/
    #Classification/g7.sample_dl/pageinfo.json
    print("Classification/g7.sample_dl/pageinfo.json","Classification/"+path.strip()+"/pageinfo.json")
    pageinfo=json.loads(read_file("Classification/"+path.strip()+"/pageinfo.json"))
    #metaclause=defaultdict(list,json.loads(read_file("Classification/"+path+"/metaclause.json")))
    #print(metaclause)
    # blob=bucket.blob("Critical/"+path+"/pageinfo.json")
    # url=blob.generate_signed_url(
    #     expiration=datetime.timedelta(minutes=2),
    #     method='get',
    #     version='v4',response_type="png"
    # )
    singed_list=dict()
    for key,val in pageinfo.items():
        singed_list[key]=[get_signed_url2(val,"get")]
    #print(singed_list)
    print(time.time()-st)
    return JSONResponse(singed_list)
@app.get('/deleteRec')
def deleteRec(request:Request):
    slno=request.query_params.get('slno')
    print("uuid",slno)
    mongoDB.deleteRec(slno)
    print(slno,"deleted successfully")
    return "completed"
@app.get('/getDocType')
def getDocType():
    return mongoDB.getAllDocType()
@app.get('/keyingscreen')
def keyingscreen(request:Request):
    return render_template("keyingscreen.html",{"request":request})
@app.post("/updateDoc")
def updateDoc(uuid:str=Form(),doc_type:str=Form()):
    print(uuid,doc_type)
    mongoDB.updateDoc(uuid,doc_type)
    return "complleted"
print("hello",__name__)
if __name__ == "__main__":
    print("in same main")
    #uvicorn.run("main:app",debug = True, port = 5000,host='0.0.0.0',access_log=True,reload=False,log_level=True)
    uvicorn.run(app,debug = True, port = 5000,host='0.0.0.0')