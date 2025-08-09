# Dual-Gain P Control in AstraArmController Firmware

## 1. What is Dual-Gain P Control?

**Dual-gain P control** is a proportional control strategy where the proportional gain (`Kp`) changes depending on the size of the control error. Instead of using a single gain for all error magnitudes, the controller uses:
- A **lower gain** for small errors (for stability and precision)
- A **higher gain** for large errors (for faster response)

This approach combines the benefits of fast movement and precise positioning.

---

## 2. Why Use Dual-Gain P Control?

- **Fast response for large errors:** When the arm is far from the target, a higher gain helps it move quickly.
- **Stable, precise control for small errors:** As the arm approaches the target, a lower gain prevents overshoot and oscillation, improving accuracy.
- **Reduces the need for aggressive integral or derivative action,** making tuning easier and the system more robust.

---

## 3. How is it Implemented in the Code?

In the AstraArmController firmware, dual-gain P control is implemented in the PID loop for each joint:

```cpp
// Parameters (tunable at runtime)
float pidtune_kp;              // Base proportional gain
float pidtune_kp2;             // Higher proportional gain for large errors
float pidtune_kp2_err_point;   // Error threshold for switching gains

// In the control loop (dualMotor.cpp):
float err = goal_pos[i] - last_pos[i];
float p_out = kp * err
    + (kp2 - kp) * (err > kp2_err_point ? err - kp2_err_point : 0)
    + (kp2 - kp) * (err < -kp2_err_point ? err + kp2_err_point : 0);
```

- For |error| < `kp2_err_point`, only `kp` is used.
- For |error| > `kp2_err_point`, the gain increases to `kp2` for the portion of the error outside the threshold.

**Graphically:**
- The proportional gain curve is flat (low) near zero error, and ramps up (high) for large errors.

---

## 4. How to Tune Dual-Gain P Control

- **`kp`**: Set for stable, precise control when the arm is close to the target (small errors).
- **`kp2`**: Set for fast, aggressive movement when the arm is far from the target (large errors).
- **`kp2_err_point`**: Set the error threshold (in encoder counts) where the gain switches from `kp` to `kp2`.

**Tuning steps:**
1. Start with `kp2 = kp` (single-gain behavior). Tune `kp` for good precision.
2. Increase `kp2` to speed up large moves, but not so high that it causes instability.
3. Adjust `kp2_err_point` to control where the gain transition happens.

---

## 5. Effect in Single-Motor-Per-Joint Setup

- **Dual-gain P control is a software feature** and works regardless of whether each joint has one or multiple motors.
- In the current single-motor-per-joint firmware, each joint benefits from dual-gain P control for:
  - Fast, smooth large moves
  - Stable, accurate final positioning
- The logic is applied to each joint's error and output, just as before.

---

## 6. Practical Example

Suppose:
- `kp = 1.0`
- `kp2 = 3.0`
- `kp2_err_point = 100`

- For errors between -100 and 100, the gain is 1.0 (precise, stable).
- For errors beyond ±100, the gain ramps up to 3.0 (fast correction).

---

## 7. Summary

Dual-gain P control is a powerful, flexible way to get both speed and precision from your robotic arm, and is fully supported in the AstraArmController firmware for each joint, even after switching to a single-motor-per-joint design. 