from cv import UIMatcher
from util import *
import uiautomator2 as u2
import random




class Automator:
    def __init__(self, device: str, upgrade_list: list, harvest_filter:list, auto_task = False, auto_policy = True, speedup = True):
        """
        device: 如果是 USB 连接，则为 adb devices 的返回结果；如果是模拟器，则为模拟器的控制 URL 。
        """
        self.d = u2.connect(device)
        self.upgrade_list = upgrade_list
        self.harvest_filter = harvest_filter
        self.dWidth, self.dHeight = self.d.window_size()
        print(self.dWidth, self.dHeight)
        self.appRunning = False
        self.auto_task = auto_task
        self.auto_policy = auto_policy
        self.loot_speedup = speedup
        
    def start(self):
        """
        启动脚本，请确保已进入游戏页面。
        """
        cnt = 0
        while True:
            # 判断jgm进程是否在前台, 最多等待20秒，否则唤醒到前台
            if self.d.app_wait("com.tencent.jgm", front=True,timeout=20):
                if not self.appRunning:
                    # 从后台换到前台，留一点反应时间
                    print("App is front. JGM agent start in 5 seconds")
                    time.sleep(5) 
                self.appRunning = True
            else:
                self.d.app_start("com.tencent.jgm")
                self.appRunning = False
                continue
            
            # 判断是否可升级政策
            self.check_policy()
            # 判断是否可完成任务
            self.check_task()
            # 判断货物那个叉叉是否出现

            good_id = self._has_good()
            if len(good_id) > 0:
                print("[%s] Train come."%time.asctime())
                self.harvest(self.harvest_filter, good_id)
            else:
                print("[%s] No Train."%time.asctime())
                findSomething = True
            
            # 再看看是不是有货没收，如果有就重启app
            good_id = self._has_good()
            if len(good_id) > 0 and self.loot_speedup:
                self.d.app_stop("com.tencent.jgm")
                print("[%s] Reset app."%time.asctime())
                time.sleep(2)
                # 重新启动app
                self.d.app_start("com.tencent.jgm")
                continue

            # 简单粗暴的方式，处理 “XX之光” 的荣誉显示。
            # 不管它出不出现，每次都点一下 确定 所在的位置
            self.d.click(550/1080, 1650/1920)
            self.upgrade([random.choice(self.upgrade_list)])
            # 滑动屏幕，收割金币。
            self.swipe()

            #判断点不点红包
            # cnt += 1
            # self.d.click(0.4, 0.958)
            # time.sleep(2)
            # print("detect redpocket")
            # self._have_redpocket()
            # print("detect finished")
            # self.d.click(0.1, 0.958)
            # time.sleep(2)

    def upgrade(self, upgrade_list):
        self._open_upgrade_interface()
        for building,count in upgrade_list:
           self._upgrade_one_with_count(building,count) 
        self._close_upgrade_interface()
    
    def swipe(self):
        """
        滑动屏幕，收割金币。
        """
        try:
            # print("[%s] Swiped."%time.asctime())
            for i in range(3):
                # 横向滑动，共 3 次。
                sx, sy = BUILDING_POSITIONS[i * 3 + 1]
                ex, ey = BUILDING_POSITIONS[i * 3 + 3]
                self.d.swipe(sx-0.1, sy+0.05, ex, ey)
        except(Exception):
            # 用户在操作手机，暂停10秒
            time.sleep(10)

    def harvest(self,building_filter,goods:list):
        '''
        新的傻瓜搬货物方法,先按住截图判断绿光探测货物目的地,再搬
        '''
        short_wait()
        for good in goods:
            pos_id = self.guess_good(good)
            if pos_id != 0 and pos_id in building_filter:
                # 搬5次
                self._move_good_by_id(good, BUILDING_POSITIONS[pos_id], times=4)
                short_wait()
      
    def guess_good(self, good_id):
        '''
        按住货物，探测绿光出现的位置
        这一段应该用numpy来实现，奈何我对numpy不熟。。。
        '''
        diff_screen = self.get_screenshot_while_touching(GOODS_POSITIONS[good_id])
        pos_ID = 0   
        for pos_ID in range(1,10):
            # print('hhhh')
            x,y = GOODS_SAMPLE_POSITIONS[pos_ID]
            lineCount = 0
            for line in range(-2,6): #划8条线, 任意2条判定成功都算
                R,G,B = 0,0,0
                for i in range(-10,10):# 取一条线上20个点,取平均值
                    r,g,b = UIMatcher.getPixel(diff_screen, (x+1.73*i)/540,(y+line+i)/960)
                    R+=r
                    G+=g
                    B+=b
                # 如果符合绿光的条件
                if R/20 >220   and G/20 < 70:
                    lineCount += 1           
            if lineCount > 1:
                return pos_ID
        return 0

    def get_screenshot_while_touching(self, location, pressed_time=0.2):
        '''
        Get screenshot with screen touched.
        '''
        screen2 = self.d.screenshot(format="opencv")
        h,w = len(screen2),len(screen2[0])
        x,y = (location[0] * w,location[1] *h)
        # 按下
        self.d.touch.down(x,y)
        # print('[%s]Tapped'%time.asctime())
        time.sleep(pressed_time)
        # 截图
        screen = self.d.screenshot(format="opencv")
        # print('[%s]Screenning'%time.asctime())
        # 松开
        self.d.touch.up(x,y)
        # 返回按下前后两幅图的差值
        return screen- screen2

    def check_policy(self):
        if not self.auto_policy:
            return
        # 看看政策中心那里有没有冒绿色箭头气泡
        if len(UIMatcher.findGreenArrow(self.d.screenshot(format="opencv"))):
            # 打开政策中心
            self.d.click(0.206, 0.097)
            mid_wait()
            # 确认升级
            self.d.click(0.077, 0.122)
            # 拉到顶
            self._slide_to_top()
            # 开始找绿色箭头,找不到就往下滑,最多划5次
            for i in range(5):
                screen = self.d.screenshot(format="opencv")
                arrows = UIMatcher.findGreenArrow(screen)
                if len(arrows):
                    x,y = arrows[0]
                    self.d.click(x,y) # 点击这个政策
                    short_wait()
                    self.d.click(0.511, 0.614) # 确认升级
                    print("[%s] Policy upgraded.    ++++++"%time.asctime())
                    self._back_to_main()

                    return
                # 如果还没出现绿色箭头，往下划
                self.d.swipe(0.482, 0.809, 0.491, 0.516,duration = 0.3)
            self._back_to_main()

    def check_task(self):
        if not self.auto_task:
            return
        # 看看任务中心有没有冒黄色气泡
        screen = self.d.screenshot(format="opencv")
        if UIMatcher.findTaskBubble(screen):
            self.d.click(0.16, 0.84) # 打开城市任务
            short_wait()
            self.d.click(0.51, 0.819) # 点击 完成任务
            print("[%s] Task finished.    ++++++"%time.asctime())
            self._back_to_main()

    def _open_upgrade_interface(self):
        screen = self.d.screenshot(format="opencv")
        # 判断升级按钮的颜色，蓝比红多就处于正常界面，反之在升级界面
        R, G, B = UIMatcher.getPixel(screen,0.974,0.615)
        if B > R:
            self.d.click(0.9, 0.57)

    def _close_upgrade_interface(self):
        screen = self.d.screenshot(format="opencv")
        # 判断升级按钮的颜色，蓝比红多就处于正常界面，反之在升级界面
        R, G, B = UIMatcher.getPixel(screen,0.974,0.615)
        if B < R:
            self.d.click(0.9, 0.57)

    def _have_redpocket(self):
        screen = self.d.screenshot(format="opencv")
        R, G, B = UIMatcher.getPixel(screen, 0.184,0.263)
        while True:
            if R < G:
                self.d.click(0.184,0.263)
                while True:
                    screen_1 = self.d.screenshot(format="opencv")
                    R_1, G_1, B_1 = UIMatcher.getPixel(screen_1, 0.487, 0.831)
                    if R_1 > G_1:
                        self.d.click(0.184,0.263)
                    else: break
            else: break

        R, G, B = UIMatcher.getPixel(screen, 0.503,0.263)
        while True:
            if R < G:
                self.d.click(0.503,0.317)
                while True:
                    screen_1 = self.d.screenshot(format="opencv")
                    R_1, G_1, B_1 = UIMatcher.getPixel(screen_1, 0.487, 0.831)
                    if R_1 > G_1:
                        self.d.click(0.503, 0.267)
                    else: break
            else:
                break


        R, G, B = UIMatcher.getPixel(screen, 0.811,0.263)
        while True:
            if R < G:
                self.d.click(0.811,0.317)
                while True:
                    screen_1 = self.d.screenshot(format="opencv")
                    R_1, G_1, B_1 = UIMatcher.getPixel(screen_1, 0.487, 0.831)
                    if R_1 > G_1:
                        self.d.click(0.811, 0.263)
                    else: break
            else:break


    def _upgrade_one_with_count(self,id,count):
        sx, sy=BUILDING_POSITIONS[id]
        self.d.click(sx, sy)
        time.sleep(0.3)
        for i in range(count):
            self.d.click(0.798, 0.884)
            # time.sleep(0.1)
       
    def _move_good_by_id(self, good: int, source, times=1):
        try:
            sx, sy = GOODS_POSITIONS[good]
            ex, ey = source
            for i in range(times):
                self.d.drag(sx, sy, ex, ey, duration = 0.1)
                short_wait()
        except(Exception):
            pass    

    def _has_good(self):
        '''
        返回有货的位置列表
        '''
        good_list = []
        screen = self.d.screenshot(format="opencv")  
        for good_id in CROSS_POSITIONS.keys():
            if self._detect_cross(screen, CROSS_POSITIONS[good_id]):
                good_list.append(good_id)
        return good_list
       
    def _detect_cross(self, screen, positon):
        x,y = positon
        # print(x,y)
        R,G,B = 0,0,0
        for i in range(-4,4):# 取一条45度线线上8个点,取平均值
            r,g,b = UIMatcher.getPixel(screen, x+i/self.dWidth,y+i/self.dHeight)
            R+=r
            G+=g
            B+=b
        # 如果符合叉叉（白色）的条件
        if R/8 >250 and G/8 > 250 and B/8 > 250:
            return True
        return False

    def _slide_to_top(self):
        for i in range(3):
            self.d.swipe(0.488, 0.302,0.482, 0.822)
            short_wait()

    def _back_to_main(self):
        for i in range(3):
            self.d.click(0.057, 0.919)
            short_wait()
