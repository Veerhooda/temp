/*
 * Assignment 6: Fractal Patterns (Koch Snowflake & Bezier Curve Tree)
 * ---------------------------------------------------------------------
 * Demonstrates:
 *   1. Koch Snowflake Fractal using recursive line subdivision
 *   2. Geometric derivation of equilateral peak using 60-degree rotation
 *   3. Bezier Curves via De Casteljau's Midpoint Subdivision Algorithm
 *   4. Recursive Fractal Tree using curved Bezier branches
 *
 * Compilation Commands:
 *   Linux:   g++ ass6_opengl.cpp -o ass6_opengl -lGL -lGLU -lglut -lm
 *   Windows: g++ ass6_opengl.cpp -o ass6_opengl -lfreeglut -lopengl32 -lglu32
 *
 * Run (Linux):   ./ass6_opengl
 * Run (Windows): ass6_opengl.exe
 */

#include <GL/glut.h>

#include <iostream>
#include <cmath>

using namespace std;

// Window dimensions
const int WINDOW_WIDTH  = 640;
const int WINDOW_HEIGHT = 480;
const float PI = 3.14159265358979323846f;

int fractalChoice = 1; // 1 = Koch Snowflake, 2 = Bezier Tree
int recursionDepth = 3;

/*
 * =====================================================================
 * 1. KOCH CURVE ALGORITHM
 * =====================================================================
 * Theory:
 *   Given segment P1(x1, y1) to P5(x5, y5):
 *     1. Base case: If depth == 0, draw line P1 -> P5.
 *     2. Divide into 3 equal segments:
 *          P2 = P1 + (1/3) * (P5 - P1)
 *          P4 = P1 + (2/3) * (P5 - P1)
 *     3. Construct equilateral triangle peak P3 on segment P2-P4:
 *          Vector V = P4 - P2 = (dx, dy)
 *          Rotate V by 60 degrees (pi/3) counter-clockwise:
 *            x3 = x2 + dx * cos(60°) - dy * sin(60°)
 *            y3 = y2 + dx * sin(60°) + dy * cos(60°)
 *     4. Recursively call Koch on the 4 segments:
 *          P1->P2, P2->P3, P3->P4, P4->P5.
 */
void drawKochCurve(int depth, float x1, float y1, float x5, float y5) {
    if (depth == 0) {
        glVertex2f(x1, y1);
        glVertex2f(x5, y5);
        return;
    }

    // Vector from P1 to P5 divided by 3
    float dx = (x5 - x1) / 3.0f;
    float dy = (y5 - y1) / 3.0f;

    // First trisection point
    float x2 = x1 + dx;
    float y2 = y1 + dy;

    // Second trisection point
    float x4 = x1 + 2.0f * dx;
    float y4 = y1 + 2.0f * dy;

    // Equilateral peak P3: rotate vector (dx, dy) by +60 degrees
    // cos(60°) = 0.5, sin(60°) = sqrt(3)/2 ≈ 0.866025
    float cos60 = 0.5f;
    float sin60 = 0.86602540378f;
    float x3 = x2 + (dx * cos60 - dy * sin60);
    float y3 = y2 + (dx * sin60 + dy * cos60);

    // Recursively draw the 4 sub-segments
    drawKochCurve(depth - 1, x1, y1, x2, y2);
    drawKochCurve(depth - 1, x2, y2, x3, y3);
    drawKochCurve(depth - 1, x3, y3, x4, y4);
    drawKochCurve(depth - 1, x4, y4, x5, y5);
}

// Draw Koch Snowflake: 3 Koch curves forming an equilateral triangle
void drawKochSnowflake(int depth) {
    float centerX = WINDOW_WIDTH / 2.0f;
    float centerY = WINDOW_HEIGHT / 2.0f + 10.0f;
    float side = 300.0f;
    float height = side * 0.86602540378f; // side * sin(60°)

    // 3 vertices of an equilateral triangle
    float ax = centerX - side / 2.0f, ay = centerY - height / 3.0f;
    float bx = centerX + side / 2.0f, by = centerY - height / 3.0f;
    float cx = centerX,               cy = centerY + 2.0f * height / 3.0f;

    glColor3f(0.2f, 0.9f, 1.0f); // Icy Cyan
    glLineWidth(1.5f);
    glBegin(GL_LINES);
        // Note: Clockwise order ensures the peaks point outward
        drawKochCurve(depth, ax, ay, cx, cy);
        drawKochCurve(depth, cx, cy, bx, by);
        drawKochCurve(depth, bx, by, ax, ay);
    glEnd();
}

/*
 * =====================================================================
 * 2. BEZIER CURVE & FRACTAL TREE ALGORITHM
 * =====================================================================
 * De Casteljau's Midpoint Subdivision:
 *   Subdivides 4 control points (P1, P2, P3, P4) at midpoint t = 0.5
 *   to render a smooth cubic Bezier curve.
 */
void drawBezierSegment(float x1, float y1, float x2, float y2,
                       float x3, float y3, float x4, float y4, int depth) {
    if (depth == 0) {
        glVertex2f(x1, y1);
        glVertex2f(x4, y4);
        return;
    }

    // 1st level midpoints
    float m1x = (x1 + x2) / 2.0f, m1y = (y1 + y2) / 2.0f;
    float m2x = (x2 + x3) / 2.0f, m2y = (y2 + y3) / 2.0f;
    float m3x = (x3 + x4) / 2.0f, m3y = (y3 + y4) / 2.0f;

    // 2nd level midpoints
    float m4x = (m1x + m2x) / 2.0f, m4y = (m1y + m2y) / 2.0f;
    float m5x = (m2x + m3x) / 2.0f, m5y = (m2y + m3y) / 2.0f;

    // 3rd level midpoint on curve
    float m6x = (m4x + m5x) / 2.0f, m6y = (m4y + m5y) / 2.0f;

    // Subdivide into left and right halves
    drawBezierSegment(x1, y1, m1x, m1y, m4x, m4y, m6x, m6y, depth - 1);
    drawBezierSegment(m6x, m6y, m5x, m5y, m3x, m3y, x4, y4, depth - 1);
}

// Recursive Fractal Tree
void drawFractalTree(float startX, float startY, float angle, float branchLen, int depth) {
    if (depth <= 0 || branchLen < 2.0f) return;

    // End point of this branch
    float endX = startX + branchLen * cos(angle);
    float endY = startY + branchLen * sin(angle);

    // Control points to give natural curvature to the branch
    float ctrl1X = startX + branchLen * 0.35f * cos(angle + 0.2f);
    float ctrl1Y = startY + branchLen * 0.35f * sin(angle + 0.2f);
    float ctrl2X = startX + branchLen * 0.70f * cos(angle - 0.15f);
    float ctrl2Y = startY + branchLen * 0.70f * sin(angle - 0.15f);

    // Foliage color gradient: brown trunk transitioning to green leaves
    float green = 0.3f + 0.7f * (float)(recursionDepth - depth + 1) / recursionDepth;
    glColor3f(0.25f, green, 0.1f);

    glBegin(GL_LINES);
        drawBezierSegment(startX, startY, ctrl1X, ctrl1Y, ctrl2X, ctrl2Y, endX, endY, 3);
    glEnd();

    // Branch into 2 child branches with angle divergence and shorter length
    float branchScale = 0.72f;
    float spreadAngle = 0.45f; // ~26 degrees
    drawFractalTree(endX, endY, angle + spreadAngle, branchLen * branchScale, depth - 1);
    drawFractalTree(endX, endY, angle - spreadAngle, branchLen * branchScale, depth - 1);
}

// =====================================================================
// OpenGL Display Callback
// =====================================================================
void display() {
    glClear(GL_COLOR_BUFFER_BIT);

    if (fractalChoice == 1) {
        drawKochSnowflake(recursionDepth);
    } else {
        // Draw ground line
        glColor3f(0.5f, 0.3f, 0.1f);
        glLineWidth(2.0f);
        glBegin(GL_LINES);
            glVertex2f(0, 50); glVertex2f(WINDOW_WIDTH, 50);
        glEnd();

        // Draw tree starting from bottom center, growing vertically upwards (angle = 90 deg = pi/2)
        drawFractalTree(WINDOW_WIDTH / 2.0f, 50.0f, PI / 2.0f, 110.0f, recursionDepth);
    }

    glFlush();
}

// =====================================================================
// Main Function with User Menu
// =====================================================================
int main(int argc, char** argv) {
    cout << "=================================================\n";
    cout << "  Assignment 6: Fractal Patterns Generator       \n";
    cout << "=================================================\n";

    cout << "\nChoose Fractal Pattern:\n";
    cout << "  1. Koch Snowflake (Snowflake Fractal)\n";
    cout << "  2. Bezier Fractal Tree (Organic Branching)\n";
    cout << "Enter choice (1 or 2): ";
    cin >> fractalChoice;

    cout << "\nEnter Recursion Depth / Iterations (Recommended 3 to 5): ";
    cin >> recursionDepth;

    if (recursionDepth < 1) recursionDepth = 1;
    if (recursionDepth > 6) {
        cout << "Warning: Depths > 6 generate millions of segments. Capping at 6 for performance.\n";
        recursionDepth = 6;
    }

    glutInit(&argc, argv);
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT);
    glutInitWindowPosition(100, 100);
    glutCreateWindow("Assignment 6: Koch Snowflake & Bezier Fractals");

    // Standard Cartesian coordinates: (0,0) at bottom-left, Y grows upwards
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT);

    glutDisplayFunc(display);
    glutMainLoop();
    return 0;
}
