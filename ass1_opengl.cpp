/*
 * Assignment 1: Line Drawing Algorithms (DDA & Bresenham)
 * --------------------------------------------------------
 * Demonstrates:
 *   1. DDA (Digital Differential Analyzer) Line Algorithm
 *   2. Bresenham's Line Drawing Algorithm (handles all slopes/octants)
 *   3. Line Styles: Simple/Solid, Dotted, Dashed, Thick
 *
 * Compilation Commands:
 *   Linux:   g++ ass1_opengl.cpp -o ass1_opengl -lGL -lGLU -lglut
 *   Windows: g++ ass1_opengl.cpp -o ass1_opengl -lfreeglut -lopengl32 -lglu32
 *
 * Run (Linux):   ./ass1_opengl
 * Run (Windows): ass1_opengl.exe
 */

#include <GL/glut.h>

#include <iostream>
#include <cmath>
#include <vector>

using namespace std;

// Window dimensions
const int WINDOW_WIDTH = 640;
const int WINDOW_HEIGHT = 480;

// Structure to store a 2D integer pixel coordinate
struct Pixel {
    int x, y;
};

// Global list of pixels to draw
vector<Pixel> linePixels;

// Helper: Add a pixel with thickness if requested
void addPixel(int x, int y, int style, int stepIndex) {
    bool shouldDraw = false;

    // Determine whether to draw based on style
    if (style == 1) {
        // 1. Solid / Simple line: draw every pixel
        shouldDraw = true;
    } else if (style == 2) {
        // 2. Dotted line: draw 1 pixel, skip 3 pixels
        shouldDraw = (stepIndex % 4 == 0);
    } else if (style == 3) {
        // 3. Dashed line: draw 6 pixels, skip 4 pixels
        shouldDraw = ((stepIndex % 10) < 6);
    } else if (style == 4) {
        // 4. Thick line: draw solid, plus adjacent pixels for thickness
        shouldDraw = true;
    }

    if (shouldDraw) {
        linePixels.push_back({x, y});
        if (style == 4) {
            // Draw neighboring pixels to increase thickness
            linePixels.push_back({x + 1, y});
            linePixels.push_back({x - 1, y});
            linePixels.push_back({x, y + 1});
            linePixels.push_back({x, y - 1});
        }
    }
}

/*
 * =====================================================================
 * 1. DDA (Digital Differential Analyzer) Algorithm
 * =====================================================================
 * Theory:
 *   - Calculates differences: dx = x2 - x1, dy = y2 - y1.
 *   - Number of steps = max(|dx|, |dy|).
 *   - In each step:
 *       x_increment = dx / steps
 *       y_increment = dy / steps
 *   - Next pixel is rounded to nearest integer: (round(x), round(y)).
 */
void drawLineDDA(int x1, int y1, int x2, int y2, int style) {
    float dx = x2 - x1;
    float dy = y2 - y1;

    // Steps is whichever change is larger to ensure no gaps in the line
    int steps = max(abs((int)dx), abs((int)dy));

    if (steps == 0) {
        addPixel(x1, y1, style, 0);
        return;
    }

    float xIncrement = dx / steps;
    float yIncrement = dy / steps;

    float currentX = x1;
    float currentY = y1;

    for (int i = 0; i <= steps; i++) {
        addPixel((int)round(currentX), (int)round(currentY), style, i);
        currentX += xIncrement;
        currentY += yIncrement;
    }
}

/*
 * =====================================================================
 * 2. Bresenham's Line Algorithm (Handles All Octants & Slopes)
 * =====================================================================
 * Theory:
 *   - Uses ONLY integer arithmetic (addition, subtraction, shift/multiplication by 2).
 *   - Extremely fast because there is no floating-point division or rounding.
 *   - Uses a 'decision parameter' (p) to decide which pixel is closest to the true line:
 *       Case A: |m| <= 1 (dx >= dy, shallow line)
 *         Initial p = 2 * dy - dx
 *         If p < 0:  next pixel is (x + sx, y),       p = p + 2 * dy
 *         If p >= 0: next pixel is (x + sx, y + sy),  p = p + 2 * dy - 2 * dx
 *
 *       Case B: |m| > 1 (dy > dx, steep line)
 *         Initial p = 2 * dx - dy
 *         If p < 0:  next pixel is (x, y + sy),       p = p + 2 * dx
 *         If p >= 0: next pixel is (x + sx, y + sy),  p = p + 2 * dx - 2 * dy
 */
void drawLineBresenham(int x1, int y1, int x2, int y2, int style) {
    int dx = abs(x2 - x1);
    int dy = abs(y2 - y1);

    // Direction of movement (+1 or -1)
    int sx = (x2 >= x1) ? 1 : -1;
    int sy = (y2 >= y1) ? 1 : -1;

    int currentX = x1;
    int currentY = y1;
    int stepIndex = 0;

    if (dx >= dy) {
        // Case A: Shallow slope (|m| <= 1), step along X
        int p = 2 * dy - dx;
        for (int i = 0; i <= dx; i++) {
            addPixel(currentX, currentY, style, stepIndex++);
            if (p < 0) {
                p += 2 * dy;
            } else {
                currentY += sy;
                p += 2 * dy - 2 * dx;
            }
            currentX += sx;
        }
    } else {
        // Case B: Steep slope (|m| > 1), step along Y
        int p = 2 * dx - dy;
        for (int i = 0; i <= dy; i++) {
            addPixel(currentX, currentY, style, stepIndex++);
            if (p < 0) {
                p += 2 * dx;
            } else {
                currentX += sx;
                p += 2 * dx - 2 * dy;
            }
            currentY += sy;
        }
    }
}

// =====================================================================
// OpenGL Display Callback
// =====================================================================
void display() {
    glClear(GL_COLOR_BUFFER_BIT);

    // Draw Cartesian Axes (X and Y passing through origin (0,0))
    glColor3f(0.35f, 0.35f, 0.35f); // subtle gray
    glBegin(GL_LINES);
        glVertex2i(-WINDOW_WIDTH / 2, 0); glVertex2i(WINDOW_WIDTH / 2, 0); // X-axis
        glVertex2i(0, -WINDOW_HEIGHT / 2); glVertex2i(0, WINDOW_HEIGHT / 2); // Y-axis
    glEnd();

    // Draw the computed line pixels
    glColor3f(1.0f, 1.0f, 0.0f); // Bright yellow
    glPointSize(2.0f);
    glBegin(GL_POINTS);
    for (const auto& pt : linePixels) {
        glVertex2i(pt.x, pt.y);
    }
    glEnd();

    glFlush();
}

// =====================================================================
// Main Function with User Menu
// =====================================================================
int main(int argc, char** argv) {
    cout << "=================================================\n";
    cout << "  Assignment 1: Line Drawing (DDA & Bresenham)  \n";
    cout << "=================================================\n";

    cout << "\nChoose Algorithm:\n";
    cout << "  1. DDA Algorithm\n";
    cout << "  2. Bresenham Algorithm\n";
    cout << "Enter choice (1 or 2): ";
    int algoChoice;
    cin >> algoChoice;

    cout << "\nChoose Line Style:\n";
    cout << "  1. Simple (Solid)\n";
    cout << "  2. Dotted\n";
    cout << "  3. Dashed\n";
    cout << "  4. Thick\n";
    cout << "Enter style (1-4): ";
    int styleChoice;
    cin >> styleChoice;

    cout << "\nCoordinate Input:\n";
    cout << "  1. Use Default Preset Line: (-180, -120) to (200, 150)\n";
    cout << "  2. Enter Custom Coordinates (relative to center 0,0)\n";
    cout << "Enter option (1 or 2): ";
    int coordChoice;
    cin >> coordChoice;

    int x1 = -180, y1 = -120, x2 = 200, y2 = 150;
    if (coordChoice == 2) {
        cout << "Enter Start Point (x1 y1): ";
        cin >> x1 >> y1;
        cout << "Enter End Point   (x2 y2): ";
        cin >> x2 >> y2;
    }

    // Run the selected line algorithm
    if (algoChoice == 1) {
        cout << "\nRunning DDA Algorithm...\n";
        drawLineDDA(x1, y1, x2, y2, styleChoice);
    } else {
        cout << "\nRunning Bresenham Algorithm...\n";
        drawLineBresenham(x1, y1, x2, y2, styleChoice);
    }

    cout << "Generated " << linePixels.size() << " points. Opening window...\n";

    // Initialize GLUT window
    glutInit(&argc, argv);
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT);
    glutInitWindowPosition(100, 100);
    glutCreateWindow("Assignment 1: DDA & Bresenham Line Drawing");

    // Set 2D Orthographic Projection with (0,0) at the center
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    gluOrtho2D(-WINDOW_WIDTH / 2, WINDOW_WIDTH / 2, -WINDOW_HEIGHT / 2, WINDOW_HEIGHT / 2);

    glutDisplayFunc(display);
    glutMainLoop();
    return 0;
}
