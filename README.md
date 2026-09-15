# Computer Graphics Lab (OpenGL/GLUT) - Complete Study & Viva Guide

This guide provides a crystal-clear breakdown of all 7 assignments, their theoretical formulas, how to compile and run them on Linux and Windows, and frequently asked Viva/Oral exam questions with direct answers.

---

## Quick Compilation Cheatsheet

| OS                           | Compilation Command                                                | Run Command       |
| :--------------------------- | :----------------------------------------------------------------- | :---------------- |
| **Linux (Ubuntu/Debian)**    | `g++ assX_opengl.cpp -o assX_opengl -lGL -lGLU -lglut -lm`         | `./assX_opengl`   |
| **Windows (MinGW/FreeGLUT)** | `g++ assX_opengl.cpp -o assX_opengl -lfreeglut -lopengl32 -lglu32` | `assX_opengl.exe` |

> _Replace `assX` with `ass1`, `ass2`, ..., `ass7`._

---

## Assignment 1: Line Drawing (DDA & Bresenham)

### What it Does

Draws a straight line between two points $(x_1, y_1)$ and $(x_2, y_2)$ using two fundamental algorithms, supporting different styles: **Solid**, **Dotted**, **Dashed**, and **Thick**.

### 1. DDA (Digital Differential Analyzer)

- **Concept**: Differential equation approach based on $\frac{dy}{dx} = m$.
- **Formulas**:
  1. $dx = x_2 - x_1$, $dy = y_2 - y_1$
  2. $steps = \max(|dx|, |dy|)$
  3. $x_{inc} = \frac{dx}{steps}$, $y_{inc} = \frac{dy}{steps}$
  4. Loop $i$ from $0$ to $steps$:
     - Plot $(\text{round}(x), \text{round}(y))$
     - $x = x + x_{inc}$, $y = y + y_{inc}$
- **Key Characteristics**: Uses floating-point arithmetic and `round()` operations, which can be computationally slower on hardware without FPUs.

### 2. Bresenham's Line Algorithm

- **Concept**: Incremental scan conversion using **only integer arithmetic** (additions, subtractions, multiplications by 2).
- **Decision Parameter ($p$)**: Determines whether the true mathematical line is closer to the upper pixel or lower pixel.
- **Formulas for $|m| \le 1$ ($dx \ge dy$)**:
  1. $p_0 = 2dy - dx$
  2. For each step along $x$:
     - If $p_k < 0$: Next pixel is $(x+1, y)$, and $p_{k+1} = p_k + 2dy$
     - If $p_k \ge 0$: Next pixel is $(x+1, y+1)$, and $p_{k+1} = p_k + 2dy - 2dx$
- **Formulas for $|m| > 1$ ($dy > dx$)**:
  - Swap roles of $x$ and $y$: step along $y$, calculate $p_0 = 2dx - dy$.

### Viva Questions & Answers

- **Q: Why is Bresenham preferred over DDA?**
  - **A:** Bresenham uses **pure integer math**, avoiding floating-point division and rounding. This makes it faster and more hardware-friendly.
- **Q: What determines the number of steps in DDA?**
  - **A:** $steps = \max(|dx|, |dy|)$. This ensures that every unit step along the dominant axis moves by at most 1 pixel, preventing gaps in the line.

---

## Assignment 2: Bresenham's Circle Drawing

### What it Does

Draws a rasterized circle centered at $(x_c, y_c)$ with radius $r$ using the Midpoint/Bresenham circle algorithm.

### Core Concepts

1. **8-Way Symmetry**:
   - A circle is symmetric across 8 octants ($x=0, y=0, y=x, y=-x$).
   - We only compute points for the **first octant** (from $x=0$ to $x \le y$, an arc of $45^\circ$).
   - For every $(x, y)$, we plot 8 symmetric points:
     $(x_c \pm x, y_c \pm y)$ and $(x_c \pm y, y_c \pm x)$.
2. **Decision Parameter**:
   - Initial value: $p_0 = 3 - 2r$ (or $1 - r$).
   - If $p < 0$: Midpoint is inside the circle. Choose East pixel $(x+1, y)$. Update $p = p + 4x + 6$.
   - If $p \ge 0$: Midpoint is outside/on the circle. Choose South-East pixel $(x+1, y-1)$. Update $p = p + 4(x - y) + 10$.
   - Always increment $x$ by 1.

### Viva Questions & Answers

- **Q: Why do we only compute $\frac{1}{8}$th of the circle?**
  - **A:** Because of 8-way symmetry, calculating points from $0^\circ$ to $45^\circ$ allows us to mirror all other 7 octants with simple additions/subtractions.
- **Q: What is the stopping condition?**
  - **A:** When $x > y$ (the loop terminates at $45^\circ$).

---

## Assignment 3: Polygon Filling (Flood Fill & Boundary Fill)

### What it Does

Fills the interior of a 2D boundary using seed-fill algorithms upon a mouse click.

### Algorithms

1. **Flood Fill (Replacement Fill)**:
   - Replaces all pixels of a designated **interior background color** with the new **fill color**.
   - Suitable when the interior is uniformly colored.
2. **Boundary Fill**:
   - Spreads outward from the seed point until it hits pixels with a designated **boundary color**.
   - Condition to color a pixel: `pixel != boundaryColor && pixel != fillColor`.

### Why Use an Explicit Stack?

- Direct recursion on an area of $200 \times 200 = 40,000$ pixels exceeds standard call stack limits, causing a `Segmentation fault (stack overflow)`.
- Using `std::stack<pair<int,int>>` allocates memory on the **heap**, preventing crashes.

### Viva Questions & Answers

- **Q: What is the difference between 4-connected and 8-connected fill?**
  - **A:** 4-connected checks top, bottom, left, right neighbors. 8-connected also checks the 4 diagonal neighbors. 4-connected will not leak through diagonal boundaries.
- **Q: When would Flood Fill fail where Boundary Fill succeeds?**
  - **A:** If the interior of the polygon has multiple colors, Flood Fill will only replace the single target color it starts on, whereas Boundary Fill stops strictly at the boundary regardless of interior colors.

---

## Assignment 4: Cohen-Sutherland Polygon Clipping

### What it Does

Clips line segments against a rectangular clipping window $[wx_{min}, wy_{min}]$ to $[wx_{max}, wy_{max}]$ and maps the visible portions onto a display **viewport**.

### 1. 4-bit Region Outcodes (TBRL)

The 2D plane is divided into 9 regions using 4 bits:

- **Bit 3 (Top = 8)**: $y > wy_{max}$
- **Bit 2 (Bottom = 4)**: $y < wy_{min}$
- **Bit 1 (Right = 2)**: $x > wx_{max}$
- **Bit 0 (Left = 1)**: $x < wx_{min}$
- Inside window: `0000` (0)

### 2. Acceptance & Rejection Tests

- **Trivial Accept**: `(code1 | code2) == 0` (Both endpoints have code 0000; line is completely inside).
- **Trivial Reject**: `(code1 & code2) != 0` (Both share an outside edge; line is completely outside).
- **Clipping**: If neither, select the outside endpoint, compute intersection with window border using line slope $m = \frac{dy}{dx}$, and repeat.

### 3. Window-to-Viewport Transformation

Maps world coordinate $(x_w, y_w)$ inside the window to $(x_v, y_v)$ inside the viewport:
$$x_v = vx_{min} + (x_w - wx_{min}) \times \frac{vx_{max} - vx_{min}}{wx_{max} - wx_{min}}$$
$$y_v = vy_{min} + (y_w - wy_{min}) \times \frac{vy_{max} - vy_{min}}{wy_{max} - wy_{min}}$$

### Viva Questions & Answers

- **Q: What does `(code1 & code2) != 0` mean?**
  - **A:** It means both endpoints are simultaneously on the same outside side (e.g., both above the top border), so the line cannot cross the window.
- **Q: How does polygon clipping work using Cohen-Sutherland?**
  - **A:** Each edge $(V_i, V_{i+1})$ of the polygon is treated as an individual line segment and clipped independently.

---

## Assignment 5: 2D Geometric Transformations

### What it Does

Applies linear transformations to a 2D polygon and shows the original (Red) vs transformed (Green) shape.

### Transformation Formulas

1. **Translation**:
   - $x' = x + t_x$
   - $y' = y + t_y$
2. **Rotation about Origin $(0, 0)$ by angle $\theta$**:
   - $x' = x\cos\theta - y\sin\theta$
   - $y' = x\sin\theta + y\cos\theta$
3. **Rotation about an Arbitrary Point $(x_r, y_r)$**:
   - Translate to origin, rotate, translate back:
   - $x' = x_r + (x - x_r)\cos\theta - (y - y_r)\sin\theta$
   - $y' = y_r + (x - x_r)\sin\theta + (y - y_r)\cos\theta$
4. **Scaling**:
   - $x' = x \cdot s_x$
   - $y' = y \cdot s_y$
5. **Reflection**:
   - About X-axis: $x' = x, y' = -y$
   - About Y-axis: $x' = -x, y' = y$
   - About Origin: $x' = -x, y' = -y$

### Viva Questions & Answers

- **Q: Why do we use Homogeneous Coordinates ($3 \times 3$ matrices)?**
  - **A:** To represent translation, rotation, and scaling in a single uniform matrix format, allowing composite transformations through simple matrix multiplication.
- **Q: Is 2D rotation commutative?**
  - **A:** Yes, 2D rotations about the same center commute ($R_{\theta_1} R_{\theta_2} = R_{\theta_2} R_{\theta_1}$). However, rotation and translation do NOT commute.

---

## Assignment 6: Fractals (Koch Snowflake & Bezier Tree)

### What it Does

Generates recursive self-similar fractal patterns:

1. **Koch Snowflake**: Begins with an equilateral triangle, recursively replacing the middle third of each edge with an equilateral peak.
2. **Bezier Fractal Tree**: Simulates natural botanical branching using cubic Bezier curves subdivided with De Casteljau's algorithm.

### Mathematical Breakdown

- **Koch Equilateral Peak**:
  - Divide segment into 3 parts: $P_2 = P_1 + \frac{1}{3}(P_5 - P_1)$ and $P_4 = P_1 + \frac{2}{3}(P_5 - P_1)$.
  - Vector $V = (dx, dy) = P_4 - P_2$.
  - Rotate $V$ by $60^\circ$ ($\pi/3$ rad) to find peak $P_3$:
    $x_3 = x_2 + dx\cos(60^\circ) - dy\sin(60^\circ)$
    $y_3 = y_2 + dx\sin(60^\circ) + dy\cos(60^\circ)$
- **De Casteljau Midpoint Subdivision**:
  - Evaluates Bezier curve at $t = 0.5$ by taking iterative midpoints between control points $(P_0, P_1, P_2, P_3)$.

### Viva Questions & Answers

- **Q: What is the fractal dimension of a Koch curve?**
  - **A:** $D = \frac{\log 4}{\log 3} \approx 1.2619$. Each step replaces 1 segment with 4 segments of $\frac{1}{3}$ length.
- **Q: What is a Bezier curve control polygon?**
  - **A:** The convex hull formed by connecting the control points $(P_0, P_1, P_2, P_3)$ in sequence. The curve always lies within this hull.

---

## Assignment 7: Interactive Animation using C++ OOP

### What it Does

Demonstrates core Object-Oriented Programming (OOP) principles integrated into real-time interactive computer graphics:

1. **Bouncing Ball**: Simulates gravity ($v_y -= g$), wall rebounds, and ground damping ($v_y = -v_y \times 0.85$).
2. **Moving Car**: Composite object rendering with body, cabin, windows, rotating wheels, and wrap-around screen traversal.

### OOP Architecture

- **Abstract Base Class**: `GraphicObject`
  - Defines pure virtual functions: `virtual void draw() = 0;` and `virtual void update() = 0;`.
  - Virtual destructor: `virtual ~GraphicObject() {}` ensures correct derived cleanup.
- **Polymorphism**:
  - Single pointer `GraphicObject* currentObject` can point to either `BouncingBall` or `MovingCar` at runtime.
- **Double Buffering (`GLUT_DOUBLE`)**:
  - Draws onto a hidden back buffer and swaps using `glutSwapBuffers()` to eliminate screen flickering.

### Interactive Controls

- `[SPACEBAR]`: Pause / Resume animation
- `[1]`: Switch to Bouncing Ball
- `[2]`: Switch to Moving Car
- `[R]`: Reset position

### Viva Questions & Answers

- **Q: How is polymorphism demonstrated in this code?**
  - **A:** Through the base class pointer `GraphicObject* currentObject`. In the display loop, calling `currentObject->draw()` dynamically invokes either `BouncingBall::draw()` or `MovingCar::draw()` via the vtable.
- **Q: Why is double buffering necessary in computer graphics animations?**
  - **A:** In single buffering, the monitor may refresh while the scene is mid-draw, causing visual tearing and flickering. Double buffering renders to a back buffer and displays it all at once when complete.
