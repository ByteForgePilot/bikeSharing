"""补全所有缺失图表"""
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams['font.sans-serif'] = ['SimSun', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

OUT = 'd:/bicycle/report_images'
def save(name):
    plt.savefig(f'{OUT}/{name}.png', dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
def b(ax,x,y,w,h):
    ax.add_patch(plt.Rectangle((x-w/2,y-h/2),w,h,fc='white',ec='black',lw=1.2))
def a(ax,x1,y1,x2,y2):
    ax.annotate('',xy=(x2,y2),xytext=(x1,y1),arrowprops=dict(arrowstyle='->',lw=1.2,color='black'))
def t(ax,x,y,s,**kw):
    ax.text(x,y,s,ha='center',va='center',family='SimSun',color='black',**kw)
def cap(s):
    plt.text(0.5,-0.03,s,ha='center',fontsize=12,fontweight='bold',family='SimSun',color='black',transform=plt.gcf().transFigure)

# ═══════════ 图 3-1 权限申请流程图 ═══════════
fig,ax=plt.subplots(figsize=(7,6)); ax.set_xlim(0,8); ax.set_ylim(0,8); ax.axis('off')
steps=[(4,7.5,'用户点击「开始采集」'),(4,6.5,'检查关键权限\n(位置 + 录音)'),
       (6.5,5.5,'已全部授予'),(1.5,5.5,'有缺失'),(1.5,4.5,'弹出权限请求对话框'),
       (1.5,3.5,'用户同意'),(6.5,3.5,'用户拒绝'),(4,2.5,'检查存储权限\n(Android 11+ MANAGE_STORAGE)'),
       (4,1.5,'已授权 / 已回退'),(4,0.5,'启动前台服务，开始采集')]
for x,y,s in steps: b(ax,x,y,4.5,0.7); t(ax,x,y,s,fontsize=9)
arrs=[(4,7.1,4,6.85),(4,6.1,6.5,5.85),(4,6.1,1.5,5.85),(1.5,5.1,1.5,4.85),(1.5,4.1,1.5,3.85),(1.5,3.1,4,2.85),(6.5,5.1,4,2.85),(4,2.1,4,1.85),(4,1.1,4,0.85)]
for x1,y1,x2,y2 in arrs: a(ax,x1,y1,x2,y2)
# branch labels
t(ax,6.5,6.0,'关键权限齐全',fontsize=8)
ax.text(4.3,6.2,'关键权限缺失',fontsize=8,family='SimSun',color='black',rotation=60)
t(ax,2.8,4.0,'同意',fontsize=8); t(ax,6.5,3.0,'拒绝 -> Toast提示',fontsize=8)
cap('图 3-1  权限申请流程图'); plt.tight_layout(pad=2); save('图3-1_权限申请流程'); print('3-1')

# ═══════════ 图 3-2 SensorService 生命周期 ═══════════
fig,ax=plt.subplots(figsize=(7,7)); ax.set_xlim(0,8); ax.set_ylim(0,9); ax.axis('off')
steps=[(4,8.5,'onCreate()'),(4,7.5,'createNotificationChannel()'),(4,6.5,'初始化 AccelCollector / GpsCollector\nGyroCollector / AudioCollector'),(4,5.5,'startForeground(ID, 通知)'),(4,4.3,'onStartCommand(Intent)'),(1.5,3.2,'ACTION_START\nstartCollection()'),(6.5,3.2,'ACTION_STOP\npauseCollection()'),(4,2.0,'return START_STICKY'),(4,1.0,'onDestroy()'),(4,0.2,'取消协程 / 停止传感器\n关闭文件 / 释放WakeLock')]
for x,y,s in steps:
    h=0.6 if y<3 else 0.7; b(ax,x,y,5.5,h); t(ax,x,y,s,fontsize=8.5)
arrs=[(4,8.1,4,7.85),(4,7.1,4,6.85),(4,6.1,4,5.85),(4,5.1,4,4.65),(4,3.9,1.5,3.55),(4,3.9,6.5,3.55),(1.5,2.85,4,2.35),(6.5,2.85,4,2.35),(4,1.7,4,1.35),(4,0.7,4,0.55)]
for x1,y1,x2,y2 in arrs: a(ax,x1,y1,x2,y2)
cap('图 3-2  SensorService 生命周期示意图'); plt.tight_layout(pad=2); save('图3-2_SensorService生命周期'); print('3-2')

# ═══════════ 图 3-3 合并CSV稀疏列填充示意 ═══════════
fig,ax=plt.subplots(figsize=(10,2)); ax.set_xlim(0,12); ax.set_ylim(0,3); ax.axis('off')
header='timestamp_ns | 传感器类型 | ax | ay | az | 纬度 | 经度 | 速度 | 航向角 | gx | gy | gz'
ax.text(6,2.5,header,ha='center',fontsize=9,fontweight='bold',family='SimSun',color='black')
rows=[('12345678','加速度计','0.12','-0.03','9.81','','','','','','',''),
      ('12345700','陀螺仪','','','','','','','','0.01','0.00','0.05'),
      ('12345800','GPS','','','','39.90','116.38','5.42','87.3','','','')]
for i,row in enumerate(rows):
    y=1.8-i*0.6
    ax.add_patch(plt.Rectangle((0.3,y-0.22),11.4,0.44,fc='white',ec='black',lw=0.8))
    for j,cell in enumerate(row):
        ax.text(0.8+j*1.0,y,cell,ha='center',va='center',fontsize=8,family='SimSun',color='black')
    # highlight non-empty cells
    for j,cell in enumerate(row):
        if cell:
            ax.add_patch(plt.Rectangle((0.5+j*1.0,y-0.2),0.85,0.4,fc='#EEE',ec='none'))
            ax.text(0.8+j*1.0,y,cell,ha='center',va='center',fontsize=8,fontweight='bold',family='SimSun',color='black')
cap('图 3-3  合并CSV文件的稀疏列填充示意')
plt.tight_layout(pad=2); save('图3-3_CSV稀疏列填充'); print('3-3')

# ═══════════ 图 4-1 MainScreen 布局结构 ═══════════
fig,ax=plt.subplots(figsize=(6,7)); ax.set_xlim(0,7); ax.set_ylim(0,9); ax.axis('off')
ax.add_patch(plt.Rectangle((0.3,7.8),6.4,0.9,fc='white',ec='black',lw=1.5))
t(ax,3.5,8.25,'TopAppBar: 自行车数据采集',fontsize=10,fontweight='bold')
for y,h,label,detail in [(6.2,1.0,'状态卡片','就绪 / 正在采集... / 已采集: 03分25秒'),
    (4.5,1.0,'[ 再次开始 / 暂停采集 ]','满宽大按钮，64dp 高'),
    (3.0,0.7,'传感器状态','加速度计 100Hz | GPS 10Hz | 陀螺仪 50Hz | 麦克风 8kHz'),
    (2.0,0.5,'数据输出说明','传感器数据.txt + 音频.pcm + 音频_时间戳.csv'),
    (1.2,0.5,'保存位置 (采集后有值)','/Documents/自行车数据/20250610_143025/'),
    (0.4,0.5,'调试信息 (仅开发阶段)','Service 生命周期日志'),
]:
    ax.add_patch(plt.Rectangle((0.5,y-h/2),6,h,fc='white',ec='black',lw=1))
    t(ax,3.5,y+h/2-0.2,label,fontsize=9,fontweight='bold')
    t(ax,3.5,y-h/2+0.2,detail,fontsize=7.5)
cap('图 4-1  MainScreen 布局结构'); plt.tight_layout(pad=2); save('图4-1_MainScreen布局'); print('4-1')

# ═══════════ 图 4-2 正常采集启动流程 ═══════════
fig,ax=plt.subplots(figsize=(6,7)); ax.set_xlim(0,7); ax.set_ylim(0,9); ax.axis('off')
steps=[(3.5,8.5,'用户打开 App'),(3.5,7.4,'检查崩溃日志'),(5.8,6.4,'有'),(1.2,6.4,'无'),(5.8,5.3,'CrashScreen'),(3.5,5.3,'MainScreen'),(3.5,4.2,'用户点击「开始」'),(3.5,3.2,'onStartClick() 检查权限'),(3.5,2.2,'权限齐全 -> 继续'),(3.5,1.3,'startCollection()'),(3.5,0.4,'startForegroundService(ACTION_START)')]
for x,y,s in steps:
    w=5 if y<2 else 3.5; b(ax,x,y,w,0.6); t(ax,x,y,s,fontsize=8.5)
arrs=[(3.5,8.1,3.5,7.75),(3.5,7.0,5.8,6.75),(3.5,7.0,1.2,6.75),(5.8,6.0,5.8,5.65),(1.2,6.0,3.5,5.65),(3.5,4.9,3.5,4.55),(3.5,3.8,3.5,3.55),(3.5,2.8,3.5,2.55),(3.5,1.8,3.5,1.65),(3.5,0.9,3.5,0.75)]
for x1,y1,x2,y2 in arrs: a(ax,x1,y1,x2,y2)
t(ax,5.8,5.7,'崩溃日志',fontsize=8); t(ax,1.2,5.7,'无',fontsize=8)
cap('图 4-2  正常采集启动流程'); plt.tight_layout(pad=2); save('图4-2_正常采集启动流程'); print('4-2')

# ═══════════ 图 4-3 暂停流程 ═══════════
fig,ax=plt.subplots(figsize=(6,6)); ax.set_xlim(0,7); ax.set_ylim(0,7); ax.axis('off')
steps=[(3.5,6.5,'用户点击「暂停采集」'),(3.5,5.5,'onStopClick()'),(3.5,4.5,'startService(ACTION_STOP)'),(3.5,3.5,'pauseCollection()'),(3.5,2.5,'collectionJob.cancel()\n各协程 CancellationException'),(3.5,1.5,'cleanupSession()'),(3.5,0.5,'文件 flush+close / WakeLock释放\nisRunning=false / state=Idle')]
for x,y,s in steps:
    h=0.8 if y<2 else 0.7; b(ax,x,y,5.5,h); t(ax,x,y,s,fontsize=8.5)
for yt,yb in [(6.1,5.85),(5.1,4.85),(4.1,3.85),(3.1,2.85),(2.1,1.9),(1.1,0.9)]:
    a(ax,3.5,yt,3.5,yb)
cap('图 4-3  暂停流程'); plt.tight_layout(pad=2); save('图4-3_暂停流程'); print('4-3')

print('\nAll 6 new figures saved.')
