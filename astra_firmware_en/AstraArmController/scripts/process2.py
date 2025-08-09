import matplotlib.pyplot as plt
import numpy as np

TIMER_TIMEOUT_US = 15000

labels = [
    "raw_goal_pos", "raw_goal_pos2",  # Feedforward position (command)  0 1
    "goal_pos", "goal_pos2", # Feedforward position (after acceleration/deceleration planning) 2 3
    "last_pos", "last_pos2", # Feedback position (encoder reading) 4 5
    "debug_signal", "debug_signal2", # 6 7 
    "last_vel", "last_vel2", # Feedback velocity from difference 8 9
    "out", "out2" # 10 11 12
]

datas = []
    
with open("data.csv", "r") as f:
    last_pos = None
    last_vel = 0.0
    
    last_vel2 = 0
    for line in f:
        df = [float(num.strip()) for num in line.split(",")]
        if last_pos:
            vel = (df[2] - last_pos) / (TIMER_TIMEOUT_US / 1000000)
        else:
            vel = 0.0
        acc = (vel - last_vel) / (TIMER_TIMEOUT_US / 1000000)
        last_pos = df[2]
        last_vel = vel
        
        acc2 = (df[8] - last_vel2) / (TIMER_TIMEOUT_US / 1000000)
        last_vel2 = df[8]
        
        if vel < 0:
            df[10] -= 0.30385482 * vel - 61.1004804
        else:
            df[10] -= 0.30385482 * vel + 61.1004804
        
        # if abs(acc) > 100:
        df.extend([vel, acc, acc2]) # 13 14 15
        datas.append(df)

# print(datas)
datas = np.array(datas)

plt.scatter(datas[:,15], datas[:,10], c='none', marker='o', edgecolors='b') # Feedforward acceleration-torque

# plt.plot(datas[:,13]) # Feedforward velocity

# plt.hist(abs(datas[:,14]), bins=100) # Feedforward acceleration

# plt.scatter(datas[:,13], datas[:,10]) # Feedforward velocity-torque
# plt.scatter(datas[:,8], datas[:,10]) # Feedback velocity-torque

# vels = []
# tors = []
# for vel, tor in zip(datas[:,13], datas[:,10]): # Feedforward velocity-torque
#     # if vel < 0:
#     #     vel = -vel
#     #     tor = -tor
#     vels.append(vel)
#     tors.append(tor)

fit_poly = np.polyfit(datas[:,14], datas[:,10], 1)
print(fit_poly) # [ 0.30385482 61.1004804 ]

# plt.scatter(vels, tors, c='none', marker='o', edgecolors='b')
plt.plot(range(-8000, 8000, 10), np.polyval(fit_poly, range(-8000, 8000, 10)), 'r')
# plt.plot(range(0, 1500, 1), np.polyval(fit_poly, range(0, 1500, 1)) + 60, 'r', linestyle='--')
# plt.plot(range(0, 1500, 1), np.polyval(fit_poly, range(0, 1500, 1)) - 60, 'r', linestyle='--')

plt.show()