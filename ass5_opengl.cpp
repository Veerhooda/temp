/*
 * Assignment 5: 2D Geometric Transformations
 * -------------------------------------------
 * Demonstrates:
 *   1. Translation by (tx, ty)
 *   2. Rotation about Origin (0,0) by angle theta
 *   3. Rotation about Arbitrary Point (xr, yr)
 *   4. Scaling by factors (sx, sy)
 *   5. Reflection (about X-axis, Y-axis, or Origin)
 *   6. Visual side-by-side comparison: Original (Red) vs Transformed (Green)
 *
 * Compilation Commands:
 *   Linux:   g++ ass5_opengl.cpp -o ass5_opengl -lGL -lGLU -lglut -lm
 *   Windows: g++ ass5_opengl.cpp -o ass5_opengl -lfreeglut -lopengl32 -lglu32
 *
 * Run (Linux):   ./ass5_opengl
 * Run (Windows): ass5_opengl.exe
 */

#include <GL/glut.h>

#include <iostream>
#include <vector>
#include <cmath>

using namespace std;

// Window dimensions
const int WINDOW_WIDTH  = 640;
const int WINDOW_HEIGHT = 480;
const float PI = 3.14159265358979323846f;

// 2D Point structure
struct Point {
    float x, y;
};

// Polygons
vector<Point> originalShape;
vector<Point> transformedShape;

string transformationName = "";

/*
 * =====================================================================
 * 1. Translation Transformation
 * =====================================================================
 * Mathematical Formula:
 *   x' = x + tx
 *   y' = y + ty
 *
 * Matrix Form:
 *   [x']   [1  0  tx] [x]
 *   [y'] = [0  1  ty] [y]
 *   [ 1]   [0  0   1] [1]
 */
void applyTranslation(float tx, float ty) {
    transformedShape.clear();
    for (const auto& p : originalShape) {
        transformedShape.push_back({p.x + tx, p.y + ty});
    }
}

/*
 * =====================================================================
 * 2. Rotation about Origin (0, 0)
 * =====================================================================
 * Mathematical Formula:
 *   x' = x * cos(theta) - y * sin(theta)
 *   y' = x * sin(theta) + y * cos(theta)
 *
 * Matrix Form:
 *   [x']   [cos(θ)  -sin(θ)  0] [x]
 *   [y'] = [sin(θ)   cos(θ)  0] [y]
 *   [ 1]   [  0        0     1] [1]
 */
void applyRotationOrigin(float angleDegrees) {
    float rad = angleDegrees * PI / 180.0f;
    float c = cos(rad);
    float s = sin(rad);

    transformedShape.clear();
    for (const auto& p : originalShape) {
        float nx = p.x * c - p.y * s;
        float ny = p.x * s + p.y * c;
        transformedShape.push_back({nx, ny});
    }
}

/*
 * =====================================================================
 * 3. Rotation about an Arbitrary Point (xr, yr)
 * =====================================================================
 * Composite Transformation:
 *   Step 1: Translate by (-xr, -yr) to move arbitrary point to origin
 *   Step 2: Rotate by theta about origin
 *   Step 3: Translate back by (+xr, +yr)
 *
 * Mathematical Formula:
 *   x' = xr + (x - xr) * cos(theta) - (y - yr) * sin(theta)
 *   y' = yr + (x - xr) * sin(theta) + (y - yr) * cos(theta)
 */
void applyRotationArbitrary(float xr, float yr, float angleDegrees) {
    float rad = angleDegrees * PI / 180.0f;
    float c = cos(rad);
    float s = sin(rad);

    transformedShape.clear();
    for (const auto& p : originalShape) {
        float dx = p.x - xr;
        float dy = p.y - yr;
        float nx = xr + (dx * c - dy * s);
        float ny = yr + (dx * s + dy * c);
        transformedShape.push_back({nx, ny});
    }
}

/*
 * =====================================================================
 * 4. Scaling Transformation
 * =====================================================================
 * Mathematical Formula:
 *   x' = x * sx
 *   y' = y * sy
 *
 * Matrix Form:
 *   [x']   [sx   0  0] [x]
 *   [y'] = [ 0  sy  0] [y]
 *   [ 1]   [ 0   0  1] [1]
 */
void applyScaling(float sx, float sy) {
    transformedShape.clear();
    for (const auto& p : originalShape) {
        transformedShape.push_back({p.x * sx, p.y * sy});
    }
}

/*
 * =====================================================================
 * 5. Reflection Transformation
 * =====================================================================
 * Types:
 *   1. About X-axis: x' = x,  y' = -y
 *   2. About Y-axis: x' = -x, y' = y
 *   3. About Origin: x' = -x, y' = -y
 */
void applyReflection(int mode) {
    transformedShape.clear();
    for (const auto& p : originalShape) {
        if (mode == 1)      transformedShape.push_back({p.x, -p.y});  // X-axis
        else if (mode == 2) transformedShape.push_back({-p.x, p.y});  // Y-axis
        else                transformedShape.push_back({-p.x, -p.y}); // Origin
    }
}

// =====================================================================
// OpenGL Display Callback
// =====================================================================
void display() {
    glClear(GL_COLOR_BUFFER_BIT);

    // Draw coordinate axes passing through origin (0,0)
    glColor3f(0.35f, 0.35f, 0.35f);
    glLineWidth(1.0f);
    glBegin(GL_LINES);
        glVertex2i(-WINDOW_WIDTH / 2, 0); glVertex2i(WINDOW_WIDTH / 2, 0); // X-axis
        glVertex2i(0, -WINDOW_HEIGHT / 2); glVertex2i(0, WINDOW_HEIGHT / 2); // Y-axis
    glEnd();

    // 1. Draw Original Polygon (Red)
    glColor3f(1.0f, 0.2f, 0.2f);
    glLineWidth(2.0f);
    glBegin(GL_LINE_LOOP);
    for (const auto& pt : originalShape) {
        glVertex2f(pt.x, pt.y);
    }
    glEnd();

    // 2. Draw Transformed Polygon (Bright Green)
    glColor3f(0.2f, 1.0f, 0.3f);
    glLineWidth(2.5f);
    glBegin(GL_LINE_LOOP);
    for (const auto& pt : transformedShape) {
        glVertex2f(pt.x, pt.y);
    }
    glEnd();

    glFlush();
}

// =====================================================================
// Main Function with User Menu
// =====================================================================
int main(int argc, char** argv) {
    cout << "=================================================\n";
    cout << "  Assignment 5: 2D Geometric Transformations    \n";
    cout << "=================================================\n";

    // Setup a default initial shape: Right-angled Triangle in 1st quadrant
    originalShape = {
        {30, 30},
        {120, 30},
        {30, 100}
    };

    cout << "\nInitial Shape: Triangle with vertices (30,30), (120,30), (30,100)\n";
    cout << "\nSelect Transformation:\n";
    cout << "  1. Translation\n";
    cout << "  2. Rotation about Origin (0, 0)\n";
    cout << "  3. Rotation about Arbitrary Point (xr, yr)\n";
    cout << "  4. Scaling\n";
    cout << "  5. Reflection\n";
    cout << "Enter choice (1-5): ";
    int choice;
    cin >> choice;

    if (choice == 1) {
        float tx, ty;
        cout << "Enter translation distances tx ty (e.g. 80 50): ";
        cin >> tx >> ty;
        applyTranslation(tx, ty);
        transformationName = "Translation";
    } else if (choice == 2) {
        float angle;
        cout << "Enter rotation angle in degrees (e.g. 45 or 90): ";
        cin >> angle;
        applyRotationOrigin(angle);
        transformationName = "Rotation about Origin";
    } else if (choice == 3) {
        float xr, yr, angle;
        cout << "Enter arbitrary point coordinates xr yr (e.g. 30 30): ";
        cin >> xr >> yr;
        cout << "Enter rotation angle in degrees: ";
        cin >> angle;
        applyRotationArbitrary(xr, yr, angle);
        transformationName = "Rotation about Arbitrary Point";
    } else if (choice == 4) {
        float sx, sy;
        cout << "Enter scale factors sx sy (e.g. 1.5 1.5 or 2 0.5): ";
        cin >> sx >> sy;
        applyScaling(sx, sy);
        transformationName = "Scaling";
    } else if (choice == 5) {
        int refMode;
        cout << "Reflection axis:\n  1. About X-axis\n  2. About Y-axis\n  3. About Origin\nEnter choice (1-3): ";
        cin >> refMode;
        applyReflection(refMode);
        transformationName = "Reflection";
    }

    cout << "\nDisplaying:\n";
    cout << "  [RED]   = Original Polygon\n";
    cout << "  [GREEN] = Transformed Polygon (" << transformationName << ")\n";
    cout << "Opening OpenGL window...\n";

    glutInit(&argc, argv);
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT);
    glutInitWindowPosition(100, 100);
    glutCreateWindow("Assignment 5: 2D Transformations");

    // Centered orthographic projection: (0,0) at center of the screen
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    gluOrtho2D(-WINDOW_WIDTH / 2, WINDOW_WIDTH / 2, -WINDOW_HEIGHT / 2, WINDOW_HEIGHT / 2);

    glutDisplayFunc(display);
    glutMainLoop();
    return 0;
}
