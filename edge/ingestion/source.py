import time,cv2
class VideoSource:
    def __init__(self,url): self.url=url; self.cap=None
    def open(self):
        self.cap=cv2.VideoCapture(0 if self.url=='webcam://0' else self.url); return self.cap.isOpened()
    def frames(self,sample_every=3):
        if not self.cap and not self.open(): raise RuntimeError(f'Cannot open source: {self.url}')
        i=0
        while True:
            ok,frame=self.cap.read()
            if not ok: break
            if i%sample_every==0: yield i,frame
            i+=1
        self.cap.release()
