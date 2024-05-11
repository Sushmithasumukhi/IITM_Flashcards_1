import os

import requests
from flask import Flask
from flask import render_template
from flask import request,redirect
from sqlalchemy.sql import func
from flask_restful import Resource,Api,fields,marshal_with,reqparse
from flask_sqlalchemy import SQLAlchemy
from werkzeug.exceptions import HTTPException
from flask import make_response
import json
import datetime as d

current_dir=os.path.abspath(os.path.dirname(__file__))
BASE="http://127.0.0.1:8080"
app=Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///"+os.path.join(current_dir,"database.sqlite3")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db=SQLAlchemy()
db.init_app(app)
api=Api(app)
app.app_context().push()


#-----------------------------Models----------------------------------

class User(db.Model):
    __tablename__='user'
    user_id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.Text,nullable=False,unique=True)

    
class Decks(db.Model):
    __tablename__='decks'
    user_id=db.Column(db.Integer,db.ForeignKey("user.user_id"))
    deck_id=db.Column(db.Integer,primary_key=True,nullable=False)
    deck_name=db.Column(db.Text,nullable=False)
    deck_description=db.Column(db.Text)
    score=db.Column(db.Integer, default=0)
    avg_score=db.Column(db.Integer, default=0)
    time=db.Column(db.DateTime(), default=d.datetime.now())
    
  
    
class Cards(db.Model):
    __tablename__='cards'
    card_id=db.Column(db.Integer,primary_key=True,autoincrement=True)
    deck_id=db.Column(db.Integer,db.ForeignKey("decks.deck_id"),primary_key=True)
    front=db.Column(db.Text,nullable=False)
    back=db.Column(db.Text,nullable=False)
    score=db.Column(db.Integer, default=0)
    time=db.Column(db.DateTime(), default=d.datetime.now())
    



#-------------------------Errors--------------------------------------------
    
class DeckValidationError(HTTPException):
    def __init__(self,status_code,error_code,error_message):
        message={"error_code":error_code,"error_message":error_message}
        self.response=make_response(json.dumps(message),status_code)

#------------------------------Controllers-------------------------------------------------------

global active_user,user_obj
user,record,active_user,user_obj=(None,None,None,None)

@app.route("/", methods=["GET","POST"])
def home():
    return(render_template("index.html"))




@app.route("/user/signup",methods=["GET","POST"])
def signup():
    if request.method=="GET":
        return(render_template("signup.html"))
    if request.method=="POST":
        username=request.form.get("username")
        data=User.query.filter(User.username==username).all()
        if not data:
            
            user=User(username=username)
            db.session.add(user)
            db.session.commit()
            return(render_template("new_user_create.html"))
        else:
            return(render_template("user_exists.html"))

        



@app.route("/user/login",methods=["GET","POST"])
def login():
    if request.method=="GET":
        return render_template("new_login.html")
    if request.method=="POST":
        global user
        user=request.form.get("username")
        global record
        record=User.query.filter(User.username==user)
        
        
        
        if record.all():
            global active_user,user_obj
            active_user=record.one().username
            if  not active_user:
                return("please login")
            global user_obj
            user_obj=User.query.filter(User.username==active_user).one()
            return(redirect(f"/user/dashboard"))
        else:
            return render_template("usernotexist.html")


def check_login():
    if  active_user:
        return True
    else:
        return False
        
        

@app.route("/user/dashboard")
def dashboard():
    if check_login():
       
        
        
        global user_id
        user_id=user_obj.user_id            
        deck_data=Decks.query.filter(Decks.user_id==user_id).all()
                
        return render_template("dashboard.html",User=active_user,deck_data=deck_data)
    else:
        return(render_template("session_expired.html"))
    


@app.route("/deck/add_deck",methods=["GET","POST"])
def add_deck():
    if check_login():
        
        
        if request.method=="GET":
            
            return(render_template("add_deck.html",username=user_obj.username))

        if request.method=="POST":
            deck_name=request.form.get("deck_name")
            deck_description=request.form.get("deck_description")
            
            a=requests.post(BASE+f"/api/deck/{active_user}",{"deck_name":deck_name,"deck_description":deck_description})
            if a.status_code==201:
                return(redirect(f'/user/dashboard'))
            else:
                return("Couldnt add the deck")
    else:
        return(render_template("session_expired.html"))
    


@app.route("/deck/delete/<string:deck_name>")

def deck_delete(deck_name):
    if check_login():
        
    
        global user_obj
        username=active_user
        

        req=requests.delete(BASE+f"/api/deck/{username}/{deck_name}")
        if req.status_code==202:
            return(redirect(f'/user/dashboard'))
        else:
            return(str(req.status_code))
    else:
        return(render_template("session_expired.html"))
    
@app.route("/deck/edit/<string:deck_name>",methods=['GET','POST'])
def deck_edit(deck_name):
    if check_login():
        if request.method=='GET':
            user_id=User.query.filter(User.username==active_user).one().user_id
            deck=Decks.query.filter(Decks.deck_name==deck_name,Decks.user_id==user_id).one()
            deck_id=deck.deck_id
            deck_description=deck.deck_description
            card_data=Cards.query.filter(Cards.deck_id==deck_id).all()
            return(render_template('deck.html',User=active_user,deck_name=deck_name,card_data=card_data,deck_description=deck_description))

        
    else:
        return(render_template("session_expired.html"))


@app.route("/card/edit/<string:deck_name>/<int:card_id>",methods=['GET','POST'])
def edit_card(card_id,deck_name):
    if check_login():
        if request.method=="GET":
            
            card_data=Cards.query.filter(Cards.card_id==card_id).one()
            return(render_template("edit_card.html",card=card_data,deck_name=deck_name))
        if request.method=="POST":
            new_front=request.form.get("front")
            new_back=request.form.get("back")
            card_data=Cards.query.filter(Cards.card_id==card_id).first()
            card_data.front=new_front
            card_data.back=new_back
            db.session.commit()
            return(redirect(f'/deck/edit/{deck_name}'))

        
    else:
        return(render_template("session_expired.html"))            
    
    


@app.route("/card/delete/<deck_name>/<int:card_id>")
def delete_card(card_id,deck_name):
    if check_login():
        card_data=Cards.query.filter(Cards.card_id==card_id).one()
        db.session.delete(card_data)
        db.session.commit()
        return(redirect(f'/deck/edit/{deck_name}'))

        
    else:
        return(render_template("session_expired.html"))            

@app.route("/card/<string:deck_name>/add_card", methods=["GET","POST"])
def add_card(deck_name):
    if check_login():
        if request.method=="GET":
            return(render_template("add_card.html",deck_name=deck_name))

        if request.method=="POST":
            front=request.form.get("front")
            back=request.form.get("back")
            deck_id=Decks.query.filter(Decks.deck_name==deck_name).one().deck_id
            card_data=Cards(deck_id=deck_id,front=front,back=back)

            db.session.add(card_data)
            db.session.commit()
            return(redirect(f'/deck/edit/{deck_name}'))
    
        
    else:
        return(render_template("session_expired.html"))            
    
    
    
@app.route("/deck/update/<string:deck_name>", methods=["GET","POST"])
def update_deck(deck_name):
    if check_login():
        deck_data=Decks.query.filter(Decks.deck_name==deck_name).one()
        if request.method=="GET":
            
            deck_name=deck_data.deck_name
            deck_description=deck_data.deck_description
            return(render_template("update.html",deck_name=deck_name,deck_description=deck_description))

        if request.method=="POST":
            new_deck_name=request.form.get("deck_name")
            new_deck_description=request.form.get("deck_description")
            deck_data.deck_name=new_deck_name
            deck_data.deck_description=new_deck_description
            db.session.commit()
            return(redirect(f'/deck/edit/{new_deck_name}'))
    else:
        return(render_template("session_expired.html"))
        
global deck_id,cards,dic,card_id,dscore
deck_id,cards,card_id=None,None,None
dscore=0
dic={"easy":15,"medium":10,"hard":1}
@app.route("/deck/review/<string:deck_name>", methods=["GET","POST"])

def review(deck_name):
    if check_login():
        global deck_id,cards,dscore
        if not deck_id and not cards:
            deck_id=Decks.query.filter(Decks.deck_name==deck_name).one().deck_id
            cards=Cards.query.filter(Cards.deck_id==deck_id).all()

        if request.method=="POST":
                global card_id
                card=Cards.query.filter(Cards.card_id==card_id).one()
                global dic,dscore
                dscore+=dic[request.form.get("difficulty")]
                card.score=dic[request.form.get("difficulty")]
                card.time=d.datetime.now()
                db.session.commit()
                return(redirect(f'/deck/review/{deck_name}'))
  
    
    
    
        if cards:
            
            if request.method=="GET":
                card=cards.pop()
                
                card_id=card.card_id
                return(render_template("test.html",card=card,deck_name=deck_name))
        else:
            
            
            deck_id,cards=None,None

            deck=Decks.query.filter(Decks.deck_name==deck_name).one()
            deck.score=dscore
            deck.avg_score=(deck.avg_score+dscore)/2
            deck.time= d.datetime.now()
            db.session.commit()
            
            dscore=0
            
            
            return(render_template("review_complete.html"))
        
        
    else:
        return(render_template("session_expired.html"))        
            
        

@app.route("/user/logout", methods=["GET"])
def logout():
    if request.method=="GET":
        global active_user,user_obj
        user,record,active_user,user_obj=(None,None,None,None)
        return(redirect(f'/user/login'))

@app.route("/user/exit")
def exit():
  global deck_id,cards,dic,card_id,dscore
  deck_id,cards,card_id=None,None,None
  dscore=0
  return(redirect(f'/user/dashboard'))

deck_post_args=reqparse.RequestParser()
deck_post_args.add_argument("deck_name")
deck_post_args.add_argument("deck_description")



#---------------------------------------API-------------------------------------------------------
class DeckAPI(Resource):
    def post(self,username):
        args=deck_post_args.parse_args()
        user_obj=User.query.filter(User.username==username).one()
        user_id=user_obj.user_id
        deck_name=args.get("deck_name")
        
        
        deck_description=args.get("deck_description")
        if deck_name:
            
                datacheck=Decks.query.filter(Decks.deck_name==deck_name,Decks.user_id==user_id).all()

                if not datacheck:
                    
        

                    new_deck=Decks(user_id=user_obj.user_id,deck_name=deck_name,deck_description=deck_description,score=0,avg_score=0)
                    db.session.add(new_deck)
                    db.session.commit()
                    return("Added Successfully",201)
            
                else:
                    return DeckValidationError(status_code=401, error_code='DE002', message='Deck name already exists')
         
        else:
            return DeckValidationError(status_code=400, error_code='DE001', message='Deck cant be empty')

    def delete(self,username,deck_name):
        
        user_id=User.query.filter(User.username==username).one().user_id
        deck_id=Decks.query.filter(Decks.deck_name==deck_name,Decks.user_id==user_id).one().deck_id

        del_obj=Decks.query.filter(Decks.user_id==user_id, Decks.deck_id==deck_id).all()

        if del_obj:
            
            db.session.delete(del_obj[0])
            db.session.commit()

            return("Deleted Sucessfully",202)

        else:
            return("Record Not Found",404)


    
    

        
        
    

        
    


#-------------------------api links--------------------------------------------------------------
api.add_resource(DeckAPI, '/api/deck/<string:username>','/api/deck/<string:username>/<string:deck_name>')



if __name__=="__main__":
    
    app.run(debug=True,port=8080,host='0.0.0.0')
