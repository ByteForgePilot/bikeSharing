"""生成报告全部图表——纯黑白PNG，中文命名"""
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams['font.sans-serif'] = ['SimSun', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

OUT = 'd:/bicycle/report_images'
import os; os.makedirs(OUT, exist_ok=True)

def save(name):
    plt.savefig(f'{OUT}/{name}.png', dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()

def block(ax, x, y, w, h):
    ax.add_patch(plt.Rectangle((x-w/2, y-h/2), w, h, fc='white', ec='black', lw=1.2))

def arrow(ax, x1, y1, x2, y2):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
               arrowprops=dict(arrowstyle='->', lw=1.2, color='black'))

def txt(ax, x, y, s, **kw):
    ax.text(x, y, s, ha='center', va='center', family='SimSun', color='black', **kw)

def caption(text_str):
    plt.text(0.5, -0.03, text_str, ha='center', fontsize=12, fontweight='bold',
             family='SimSun', color='black', transform=plt.gcf().transFigure)

# ══════════════════════════════════════════════════
# 图 2-1  系统总体架构
# ══════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(10, 6)); ax.set_xlim(0,10); ax.set_ylim(0,8); ax.axis('off')
for x,y,w,h,t1,t2,t3 in [
    (5,1.2,8.5,1.6,'Android 采集端','加速度计 100Hz    陀螺仪 50Hz    GPS 10Hz    麦克风 8kHz','SensorService 前台服务    纳秒级时间戳    CSV 文件输出'),
    (5,3.7,8.5,1.6,'Python 算法端','自适应窗口选取  F1 轮胎偏摆  F2 链条异响  F3 车头不正','加权调和平均 + 最小值惩罚    综合健康评分 S'),
    (5,6.2,8.5,1.6,'Web 可视化端','FastAPI 后端    ECharts 仪表盘','健康评分仪表盘    三维雷达图    信号波形频谱面板'),
]:
    block(ax,x,y,w,h)
    txt(ax,x,y+h/2-0.3,t1,fontsize=13,fontweight='bold')
    txt(ax,x,y,t2,fontsize=9.5)
    txt(ax,x,y-h/2+0.35,t3,fontsize=9)
arrow(ax,5,2.0,5,2.9); arrow(ax,5,4.5,5,5.4)
txt(ax,7,2.45,'文件读取',fontsize=7); txt(ax,7,4.95,'HTTP / JSON',fontsize=7)
caption('图 2-1  系统总体架构')
plt.tight_layout(pad=2); save('图2-1_系统总体架构'); print('2-1 done')

# ══════════════════════════════════════════════════
# 图 2-2  系统部署与运行流程
# ══════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(10, 6.5)); ax.set_xlim(0,10); ax.set_ylim(0,9); ax.axis('off')
# 三列: 巡检人员 | Android App | Python 算法
col_x = [1.5, 5, 8.5]
col_names = ['巡检人员','Android App','Python 算法']
for cx, cn in zip(col_x, col_names):
    txt(ax, cx, 8.7, cn, fontsize=11, fontweight='bold')
    ax.axvline(x=cx, ymin=0.05, ymax=0.95, color='black', lw=0.5, ls='--')
steps = [
    (col_x[0], 8.0, col_x[1], 8.0, '扫码开锁，点击开始'),
    (col_x[1], 7.3, col_x[1], 7.3, '权限检查，启动前台服务'),
    (col_x[1], 6.6, col_x[1], 6.6, '四传感器同步采集 (屏幕可关闭)'),
    (col_x[0], 5.9, col_x[1], 5.9, '骑行巡检'),
    (col_x[0], 5.2, col_x[1], 5.2, '点击暂停'),
    (col_x[1], 4.5, col_x[1], 4.5, '取消协程，关闭文件，释放 WakeLock'),
    (col_x[0], 3.8, col_x[2], 3.8, 'USB 传输文件到 PC'),
    (col_x[2], 3.1, col_x[2], 3.1, '加载数据，自适应窗口选取'),
    (col_x[2], 2.4, col_x[2], 2.4, 'F1/F2/F3 检测，综合评分'),
    (col_x[2], 1.7, col_x[2], 1.7, '输出结果 (终端 + JSON + Web)'),
    (col_x[0], 1.0, col_x[2], 1.0, '查看评分，运维决策'),
]
prev_cx, prev_y = None, None
for cx, y, _, _, s in steps:
    block(ax, cx, y, 3.5, 0.45)
    txt(ax, cx, y, s, fontsize=8)
arrow_data = [
    (col_x[0],8.0,col_x[1],7.55), (col_x[1],7.1,col_x[1],6.85), (col_x[1],6.4,col_x[1],6.15),
    (col_x[0],5.9,col_x[1],6.15), (col_x[0],5.2,col_x[1],4.75), (col_x[1],4.3,col_x[1],4.05),
    (col_x[0],3.8,col_x[2],3.35), (col_x[2],2.9,col_x[2],2.65), (col_x[2],2.2,col_x[2],1.95),
    (col_x[2],1.5,col_x[0],1.25),
]
for x1,y1,x2,y2 in arrow_data: arrow(ax, x1, y1, x2, y2)
caption('图 2-2  系统部署与运行流程')
plt.tight_layout(pad=2); save('图2-2_部署运行流程'); print('2-2 done')

# ══════════════════════════════════════════════════
# 图 3-1  传感器采样时序
# ══════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(8, 3)); ax.set_xlim(0,0.5); ax.set_ylim(0,4)
for name, interval, y in [('加速度计 100Hz',0.01,1.2),('陀螺仪 50Hz',0.02,2.4),('GPS 10Hz',0.1,3.6)]:
    ax.vlines(np.arange(0,0.5,interval),y-0.3,y+0.3,colors='black',linewidths=1.5)
    ax.text(0.52,y,name,fontsize=10,va='center',fontweight='bold',family='SimSun',color='black')
ax.set_yticks([]); ax.set_xlabel('时间 (秒)',fontsize=11,family='SimSun',color='black')
for sp in ['top','right','left']: ax.spines[sp].set_visible(False)
ax.tick_params(colors='black')
caption('图 3-1  传感器采样时序示意 (前 0.5 秒)')
plt.tight_layout(pad=2); save('图3-1_传感器采样时序'); print('3-1 done')

# ══════════════════════════════════════════════════
# 图 6-1  F1 轮胎偏摆检测流程
# ══════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(8, 6.5)); ax.set_xlim(0,10); ax.set_ylim(0,10); ax.axis('off')
steps_f1 = [
    (5,9.2,6,'Z 轴加速度采集  去直流  重采样 100Hz'),
    (5,8.0,6,'Butterworth 带通滤波 2~40Hz'),
    (5,6.8,6,'平整路面判定：1s 滑动窗口  方差 < 0.5'),
    (2.5,5.5,3.5,'flat >= 20%\n取平整路面片段'), (7.5,5.5,3.5,'flat < 20%\n降级用全部数据'),
    (5,4.3,6,'车轮转频估计：1.5~8Hz FFT 峰值搜索'),
    (5,3.1,6,'FFT 提取 A1@f, A2@2f    P = A1 + 0.5*A2'),
    (5,2.0,6,'线性评分 (P<=0.35=100, P>=1.50=0)    平整惩罚: flat<20% 上限 80 分'),
    (5,0.8,4,'输出 F1 评分 (0~100)'),
]
for x,y,w,s in steps_f1: block(ax,x,y,w,0.7); txt(ax,x,y,s,fontsize=8.5)
for a in [(5,8.8,5,8.4),(5,7.6,5,7.2),(5,6.4,5,6.0),(5,6.0,2.5,5.85),(5,6.0,7.5,5.85),
          (2.5,5.15,5,4.65),(7.5,5.15,5,4.65),(5,3.9,5,3.45),(5,2.7,5,2.35),(5,1.6,5,1.15)]:
    arrow(ax,*a)
caption('图 6-1  F1 轮胎偏摆检测算法流程')
plt.tight_layout(pad=2); save('图6-1_F1轮胎偏摆检测流程'); print('6-1 done')

# ══════════════════════════════════════════════════
# 图 7-1  F2 包络谱-倒谱双通道检测流程
# ══════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(10, 6.5)); ax.set_xlim(0,10); ax.set_ylim(0,8.5); ax.axis('off')
for x,y,w,s in [(2.5,7.5,3.5,'8kHz 音频  带通 2~4kHz\n希尔伯特变换  包络'),
                (2.5,6.4,3.5,'低通 0.5~10Hz\n包络谱 FFT  SNR@踏频'),
                (2.5,5.3,3.5,'谐波检测 (2f, 3f)\n相位一致性 (圆形方差)'),
                (2.5,4.2,3.5,'包络调制深度\nCV = std(env) / mean(env)')]:
    block(ax,x,y,w,0.6); txt(ax,x,y,s,fontsize=8)
for x,y,w,s in [(7.5,7.0,3.5,'FFT  对数功率谱'),(7.5,5.9,3.5,'IFFT  Cepstrum'),
                (7.5,4.9,3.5,'倒频率域 SNR\n(1/pedal_freq +/-15%)')]:
    block(ax,x,y,w,0.6); txt(ax,x,y,s,fontsize=8)
for yt,yb in [(7.2,6.7),(6.1,5.6),(5.0,4.5)]: arrow(ax,2.5,yt,2.5,yb)
for yt,yb in [(6.7,6.2),(5.6,5.2)]: arrow(ax,7.5,yt,7.5,yb)
block(ax,5,2.8,8,0.8); txt(ax,5,2.8,'五特征加权融合: SNR*0.35 + mod*0.25 + harm*0.10 + phase*0.10 + cepstrum*0.20',fontsize=9,fontweight='bold')
block(ax,5,1.5,5,0.7); txt(ax,5,1.5,'分段评分  F2 评分 (0~100)',fontsize=9)
arrow(ax,5,2.4,5,1.85)
txt(ax,2.5,8.1,'包络谱通道',fontsize=10,fontweight='bold')
txt(ax,7.5,8.1,'倒谱通道',fontsize=10,fontweight='bold')
caption('图 7-1  F2 包络谱-倒谱双通道检测流程')
plt.tight_layout(pad=2); save('图7-1_F2链条异响检测流程'); print('7-1 done')

# ══════════════════════════════════════════════════
# 图 8-1  F3 车头不正检测流程
# ══════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(8, 5.5)); ax.set_xlim(0,10); ax.set_ylim(0,8); ax.axis('off')
for x,y,w,s in [
    (5,7.4,6,'陀螺仪 Z 轴重采样 50Hz  5s 滑动窗口  取 gz 方差最低 30%'),
    (5,6.2,5,'质量门：最佳段 gz_std < 0.3 ?'),
    (7.5,5.1,3,'是  继续检测'), (2.5,5.1,3,'否  返回满分'),
    (5,4.0,6,'偏置估计: dtheta = deg(|median(gz_means)| * obs_time)'),
    (5,2.9,6,'符号一致性增强 (>70% 同向时轻度放大)'),
    (5,1.8,6,'加速度计侧向晃动惩罚 (stability_ratio 超标时放大等效偏角)'),
    (5,0.7,5,'评分: <= 4度 = 100,  >= 10度 = 0,  中间线性插值'),
]:
    block(ax,x,y,w,0.7); txt(ax,x,y,s,fontsize=8.5)
for a in [(5,7.0,5,6.55),(5,6.55,7.5,5.45),(5,6.55,2.5,5.45),(7.5,4.75,5,4.35),
          (5,3.6,5,3.25),(5,2.5,5,2.15),(5,1.4,5,1.05)]:
    arrow(ax,*a)
caption('图 8-1  F3 车头不正检测算法流程 (v3.2)')
plt.tight_layout(pad=2); save('图8-1_F3车头不正检测流程'); print('8-1 done')

# ══════════════════════════════════════════════════
# 图 9-1  综合评分计算流程
# ══════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(8, 4)); ax.set_xlim(0,10); ax.set_ylim(0,6); ax.axis('off')
for x,y,w,s in [(2.5,5.2,3,'F1 轮胎偏摆 (权重 0.40)'),(5,5.2,3,'F2 链条异响 (权重 0.30)'),
                (7.5,5.2,3,'F3 车头不正 (权重 0.30)')]:
    block(ax,x,y,w,0.7); txt(ax,x,y,s,fontsize=9)
block(ax,5,3.8,7,0.7); txt(ax,5,3.8,'H = 1 / (0.4/F1 + 0.3/F2 + 0.3/F3)',fontsize=9)
for x in [2.5,5,7.5]: arrow(ax,x,4.85,5,4.15)
block(ax,5,2.5,4,0.7); txt(ax,5,2.5,'S = H * (min/100)^0.7',fontsize=9)
arrow(ax,5,3.45,5,2.85)
block(ax,5,1.2,7,0.7); txt(ax,5,1.2,'S >= 75 = 推荐骑行    50~74 = 谨慎使用    < 50 = 建议换车',fontsize=9)
arrow(ax,5,2.15,5,1.55)
caption('图 9-1  综合评分计算流程')
plt.tight_layout(pad=2); save('图9-1_综合评分流程'); print('9-1 done')

# ══════════════════════════════════════════════════
# 图 9-2  penalty 曲线对比
# ══════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(7, 4))
mins = np.linspace(0,100,201)
for exp,label,ls in [(1.0,'^1.0','--'),(0.7,'^0.7 (本文)','-'),(0.6,'^0.6',':'),
                      (0.5,'^0.5','-.'),(0,'无惩罚','-.')]:
    p = np.ones_like(mins) if exp==0 else (mins/100.0)**exp
    ax.plot(mins,p,label=label,linestyle=ls,linewidth=2,
            color='black' if exp==0.7 else 'gray')
ax.set_xlabel('min(F1, F2, F3)',fontsize=11,family='SimSun',color='black')
ax.set_ylabel('penalty',fontsize=11,family='SimSun',color='black')
ax.legend(fontsize=9); ax.grid(True,alpha=0.3,color='gray')
ax.set_xlim(0,100); ax.set_ylim(0,1.05); ax.tick_params(colors='black')
for sp in ax.spines.values(): sp.set_color('black')
caption('图 9-2  不同幂指数的 penalty 曲线')
plt.tight_layout(pad=2); save('图9-2_penalty曲线'); print('9-2 done')

# ══════════════════════════════════════════════════
# 图 10-1  Web 仪表盘布局
# ══════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(9, 5)); ax.set_xlim(0,9); ax.set_ylim(0,6); ax.axis('off')
ax.add_patch(plt.Rectangle((0,5.2),9,0.7,fc='white',ec='black',lw=1.2))
txt(ax,4.5,5.55,'共享单车健康检测系统',fontsize=11,fontweight='bold')
ax.add_patch(plt.Rectangle((0.2,0.2),2.6,4.8,fc='white',ec='black',lw=1.2))
txt(ax,1.5,4.5,'评分仪表盘',fontsize=9,fontweight='bold')
ax.add_patch(plt.Rectangle((0.5,2.5),2,1.5,fc='white',ec='black',lw=1))
txt(ax,1.5,3.0,'82.8',fontsize=26,fontweight='bold')
txt(ax,1.5,2.65,'谨慎使用',fontsize=8)
txt(ax,1.5,2.1,'F1:80  F2:95  F3:82',fontsize=7)
ax.add_patch(plt.Rectangle((3.1,0.2),5.7,4.8,fc='white',ec='black',lw=1.2))
txt(ax,6,4.5,'详细分析面板',fontsize=9,fontweight='bold')
for lab,yy in [('F1 轮胎偏摆 — Z 轴波形 + FFT 频谱',3.7),('F2 链条异响 — 音频波形 + FFT 频谱',2.8),
               ('F3 车头不正 — 陀螺仪波形 + 累计偏航角',1.9),('数据摘要 (采样统计 + 窗口信息)',1.0)]:
    ax.add_patch(plt.Rectangle((3.3,yy-0.3),5.3,0.55,fc='white',ec='black',lw=0.8))
    txt(ax,3.5,yy,lab,fontsize=8)
caption('图 10-1  Web 仪表盘布局示意')
plt.tight_layout(pad=2); save('图10-1_Web仪表盘布局'); print('10-1 done')

# ══════════════════════════════════════════════════
# 图 12-1  三组数据检测结果对比
# ══════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(8, 4))
datasets = ['(3) 良好车', '(6) 中等车', '(2) 短板车']
f1,f2,f3,tt = [100,80,71.2],[95.5,94.8,92.4],[100,81.5,93.7],[98.6,72.2,65.3]
x = np.arange(3); w = 0.18
hatches = ['//','..','xx','']
for i,(vals,lab,hat) in enumerate(zip([f1,f2,f3,tt],
    ['F1 轮胎偏摆','F2 链条异响','F3 车头不正','综合评分'],hatches)):
    b = ax.bar(x+(i-1.5)*w,vals,w,label=lab,fill=False,edgecolor='black',linewidth=1.2,hatch=hat)
    for rect in b:
        ax.text(rect.get_x()+rect.get_width()/2.,rect.get_height()+0.5,
                f'{rect.get_height():.0f}',ha='center',fontsize=7,color='black')
ax.set_ylabel('评分 (0~100)',fontsize=11,family='SimSun',color='black')
ax.set_xticks(x); ax.set_xticklabels(datasets,fontsize=11,family='SimSun',color='black')
ax.set_ylim(0,115); ax.legend(fontsize=8,ncol=2)
ax.axhline(y=75,color='black',linestyle='--',linewidth=0.8)
ax.axhline(y=50,color='black',linestyle='--',linewidth=0.8)
ax.grid(axis='y',alpha=0.2,color='gray'); ax.tick_params(colors='black')
for sp in ax.spines.values(): sp.set_color('black')
caption('图 12-1  三组数据检测结果对比')
plt.tight_layout(pad=2); save('图12-1_三组数据对比'); print('12-1 done')

print('\nAll 9 figures saved.')
