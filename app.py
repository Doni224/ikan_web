import numpy as np
import keras
from keras.models import Sequential
from keras.layers import Dense,Conv2D,MaxPool2D,Dropout,BatchNormalization,Flatten,Activation
from keras.preprocessing import image 
from keras.preprocessing.image import ImageDataGenerator
import matplotlib.pyplot as plt
from keras.utils.vis_utils import plot_model
import pickle
from flask import Flask, jsonify,request,flash,redirect,render_template, session,url_for
#from flask_session import Session
from itsdangerous import json
from werkzeug.utils import secure_filename
import os
from flask_cors import CORS
from flask_restful import Resource, Api
import pymongo
import re
import jwt
import datetime


app = Flask(__name__)
# run_with_ngrok(app)
#sess = Session()
UPLOAD_FOLDER = 'foto_ikan'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.secret_key = "bigtuing"
#SECRET_KEY = 'xxxxxxxxx'
#app.config['SESSION_TYPE'] = 'filesystem'
MONGO_ADDR = 'mongodb://localhost:27017'
MONGO_DB = "db_ikan"

conn = pymongo.MongoClient(MONGO_ADDR)
db = conn[MONGO_DB]

api = Api(app)
#CORS(app)


from tensorflow.keras.models import load_model
MODEL_PATH = 'model_fish.h5'
model = load_model(MODEL_PATH,compile=False)

pickle_inn = open('num_class_fish_update.pkl','rb')
num_classes_bird = pickle.load(pickle_inn)

def allowed_file(filename):     
  return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class index(Resource):
  def post(self):

    if 'image' not in request.files:
      flash('No file part')
      return jsonify({
            "pesan":"tidak ada form image"
          })
    file = request.files['image']
    if file.filename == '':
      return jsonify({
            "pesan":"tidak ada file image yang dipilih"
          })
    if file and allowed_file(file.filename):
      filename = secure_filename(file.filename)
      file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
      path=("foto_ikan/"+filename)

      #def predict(dir):
      img=image.load_img(path,target_size=(224,224))
      img1=image.img_to_array(img)
      img1=img1/255
      img1=np.expand_dims(img1,[0])
      plt.imshow(img)
      predict=model.predict(img1)
      classes=np.argmax(predict,axis=1)
      for key,values in num_classes_bird.items():
          if classes==values:
            accuracy = float(round(np.max(model.predict(img1))*100,2))
            info = db['ikan'].find_one({'Nama_Ikan': str(key)})

            if accuracy >35:
              print("The predicted image of the fish is: "+str(key)+" with a probability of "+str(accuracy)+"%")

              db.riwayat.insert_one({'nama_file': filename, 'path': path, 'prediksi':str(key), 'akurasi':accuracy})
            
              return jsonify({
                "Nama_Ikan":str(key),
                "Accuracy":str(accuracy)+"%",
                "Jenis_Ikan" : info['Jenis_Ikan'],
                "Makanan" : info['Makanan'],
                "Status" :  info['Status']         
                
              })
            else :
              print("The predicted image of the fish is: "+str(key)+" with a probability of "+str(accuracy)+"%")
              return jsonify({
                "Message":str("Jenis Ikan belum tersedia "),
                "Accuracy":str(accuracy)+"%"               
                
              })
      
    else:
      return jsonify({
        "Message":"bukan file image"
      })

@app.route('/admin')
def admin():
    return render_template("login.html")
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        Password = request.form['password'] # .encode('utf-8')
        user = db['admin'].find_one({'username': str(username)})
        print(user)

        if user is not None and len(user) > 0:
            if Password == user['password']:
                
               token =jwt.encode(
                {
                    "username":username,
                    "exp":datetime.datetime.utcnow() + datetime.timedelta(minutes=120)
                }, app.config['SECRET_KEY'], algorithm="HS256"
            )
               print(token)
               return redirect(url_for('ikan'))
            else:
                return redirect(url_for('login'))
        else:
            return redirect(url_for('ikan'))
    else:
        return render_template('login.html')
    
    return render_template('ikan.html')
#menampilkan  daftar tamu
@app.route('/ikan')
def ikan():
    data = db['ikan'].find({})
    print(data)
    return render_template('ikan.html',ikan  = data)

@app.route('/riwayat')
def riwayat():
    dataRiwayat = db['riwayat'].find({})
    print(dataRiwayat)
    return render_template('riwayat.html',riwayat  = dataRiwayat)

@app.route('/tambahData')
def tambahData():

    return render_template('tambahData.html')

#roses memasukan data Burung ke database
@app.route('/daftarIkan', methods=["POST"])
def daftarIkan():
    if request.method == "POST":
        Nama_Ikan = request.form['Nama_Ikan']
        Jenis_Ikan = request.form['Jenis_Ikan']
        Makanan = request.form['Makanan']
        Status = request.form['Status']
        if not re.match(r'[A-Za-z]+', Nama_Ikan):
            flash("Nama harus pakai huruf Dong!")
        
        else:
            db.ikan.insert_one({'Nama_Ikan': Nama_Ikan,'Jenis':Jenis_Ikan, 'Makanan':Makanan, 'Status':Status})
            flash('Data Ikan berhasil ditambah')
            return redirect(url_for('ikan'))

    return render_template("tambahData.html")

@app.route('/editIkan/<nama>', methods = ['POST', 'GET'])
def editIkan(nama):
  
    data = db['ikan'].find_one({'nama': nama})
    print(data)
    return render_template('editIkan.html', editIkan = data)

#melakukan roses edit data
@app.route('/updateIkan/<nama>', methods=['POST'])
def updatIkan(nama):
    if request.method == 'POST':
        Nama_Ikan = request.form['Nama_Ikan']
        Jenis_Ikan = request.form['Jenis_Ikan']
        Makanan = request.form['makanan']
        Status = request.form['status']
        if not re.match(r'[A-Za-z]+', nama):
            flash("Nama harus pakai huruf Dong!")
        else:
          db.data_burung.update_one({'nama': nama}, 
          {"$set": {
            'Nama_Ikan': Nama_Ikan,  
            'jenis_Ikan':Jenis_Ikan, 
            'Makanan':Makanan, 
            'Status':Status
            }
            })

          flash('Data Ikan berhasil diupdate')
          return render_template("popUpEdit.html")

    return render_template("ikan.html")

#menghaus daftar Ikan
@app.route('/hapusIkan/<nama>', methods = ['POST','GET'])
def hapusIkan(nama):
  
    db.data_burung.delete_one({'nama': nama})
    flash(' Ikan Dihapus!')
    return redirect(url_for('ikan'))

@app.route('/hapusRiwayat/<nama_file>', methods = ['POST','GET'])
def hapusRiwayat(nama_file):
  
    db.riwayat.delete_one({'nama_file': nama_file})
    flash('Riwayat Berhasil Dihapus!')
    return redirect(url_for('riwayat'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


api.add_resource(index, "/api/image", methods=["POST"])

if __name__ == '__main__':
  

  #app.run()
  app.run(debug = True, port=5000, host='0.0.0.0')

