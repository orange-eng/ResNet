import os

import cv2
import numpy as np

import utils.utils as utils
from net.inception import InceptionResNetV1
from net.mtcnn import mtcnn


class face_rec():
    def __init__(self):
        #-------------------------#
        #   创建mtcnn的模型
        #   用于检测人脸
        #-------------------------#
        self.mtcnn_model = mtcnn()
        self.threshold = [0.5,0.6,0.8]
               
        #-----------------------------------#
        #   载入facenet
        #   将检测到的人脸转化为128维的向量
        #-----------------------------------#
        self.facenet_model = InceptionResNetV1()
        model_path = './model_data/facenet_keras.h5'
        self.facenet_model.load_weights(model_path)

        #-----------------------------------------------#
        #   对数据库中的人脸进行编码
        #   known_face_encodings中存储的是编码后的人脸
        #   known_face_names为人脸的名字
        #-----------------------------------------------#
        face_list = os.listdir("face_dataset")
        self.known_face_encodings=[]
        self.known_face_names=[]
        for face in face_list:
            name = face.split(".")[0]
            img = cv2.imread("./face_dataset/"+face)
            img = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
            #---------------------#
            #   检测人脸
            #---------------------#
            rectangles = self.mtcnn_model.detectFace(img, self.threshold)
            #---------------------#
            #   转化成正方形
            #---------------------#
            rectangles = utils.rect2square(np.array(rectangles))
            #-----------------------------------------------#
            #   facenet要传入一个160x160的图片
            #   利用landmark对人脸进行矫正
            #-----------------------------------------------#
            rectangle = rectangles[0]
            landmark = np.reshape(rectangle[5:15], (5,2)) - np.array([int(rectangle[0]), int(rectangle[1])])
            crop_img = img[int(rectangle[1]):int(rectangle[3]), int(rectangle[0]):int(rectangle[2])]
            crop_img, _ = utils.Alignment_1(crop_img,landmark)
            crop_img = np.expand_dims(cv2.resize(crop_img, (160, 160)), 0)
            #--------------------------------------------------------------------#
            #   将检测到的人脸传入到facenet的模型中，实现128维特征向量的提取
            #--------------------------------------------------------------------#
            face_encoding = utils.calc_128_vec(self.facenet_model, crop_img)

            self.known_face_encodings.append(face_encoding)
            self.known_face_names.append(name)

    def recognize(self,draw,save_flag):
        #-----------------------------------------------#
        #   人脸识别
        #   先定位，再进行数据库匹配
        #-----------------------------------------------#
        height,width,_ = np.shape(draw)
        draw_rgb = cv2.cvtColor(draw,cv2.COLOR_BGR2RGB)

        #--------------------------------#
        #   检测人脸
        #--------------------------------#
        rectangles = self.mtcnn_model.detectFace(draw_rgb, self.threshold)

        if len(rectangles)==0:
            return

        # 转化成正方形
        rectangles = utils.rect2square(np.array(rectangles,dtype=np.int32))
        rectangles[:, [0,2]] = np.clip(rectangles[:, [0,2]], 0, width)
        rectangles[:, [1,3]] = np.clip(rectangles[:, [1,3]], 0, height)

        #-----------------------------------------------#
        #   对检测到的人脸进行编码
        #-----------------------------------------------#
        face_encodings = []
        for rectangle in rectangles:
            #---------------#
            #   截取图像
            #---------------#
            landmark = np.reshape(rectangle[5:15], (5,2)) - np.array([int(rectangle[0]), int(rectangle[1])])
            crop_img = draw_rgb[int(rectangle[1]):int(rectangle[3]), int(rectangle[0]):int(rectangle[2])]
            #-----------------------------------------------#
            #   利用人脸关键点进行人脸对齐
            #-----------------------------------------------#
            crop_img,_ = utils.Alignment_1(crop_img,landmark)
            crop_img = np.expand_dims(cv2.resize(crop_img, (160, 160)), 0)

            face_encoding = utils.calc_128_vec(self.facenet_model, crop_img)
            face_encodings.append(face_encoding)

        face_names = []
        for face_encoding in face_encodings:
            #-------------------------------------------------------#
            #   取出一张脸并与数据库中所有的人脸进行对比，计算得分
            #-------------------------------------------------------#
            matches = utils.compare_faces(self.known_face_encodings, face_encoding, tolerance = 0.9)
            name = "Unknown"
            #-------------------------------------------------------#
            #   找出距离最近的人脸
            #-------------------------------------------------------#
            face_distances = utils.face_distance(self.known_face_encodings, face_encoding)
            #-------------------------------------------------------#
            #   取出这个最近人脸的评分
            #-------------------------------------------------------#
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = self.known_face_names[best_match_index]
            face_names.append(name)

        rectangles = rectangles[:,0:4]
        #-----------------------------------------------#
        #   画框~!~
        #-----------------------------------------------#
        for (left, top, right, bottom), name in zip(rectangles, face_names):
            cv2.rectangle(draw, (left, top), (right, bottom), (0, 0, 255), 2)
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(draw, name, (left , bottom - 15), font, 0.75, (255, 255, 255), 2) 
        return draw

if __name__ == "__main__":
    dududu = face_rec()
    video_path = 'video/vid2.mp4'
    video_save_path = 'video_out/vid2.mp4'
    capture = cv2.VideoCapture(video_path)
    video_fps = 25.0
    save_flag = True

    if save_flag == True:
        fourcc  = cv2.VideoWriter_fourcc(*'XVID')
        size    = (int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        out     = cv2.VideoWriter(video_save_path, fourcc, video_fps, size)


    while True:
        ret, draw = capture.read()
        frame = dududu.recognize(draw,save_flag) 
        out.write(frame)
        
        # cv2.imshow('Video', draw)
        # if cv2.waitKey(20) & 0xFF == ord('q'):
        #     break

    capture.release()
    cv2.destroyAllWindows()
