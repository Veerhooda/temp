/*
 * Assignment 2: Bresenham's Circle Drawing Algorithm
 * ----------------------------------------------------
 * Demonstrates:
 *   1. Bresenham's / Midpoint Circle Generation Algorithm
 *   2. 8-Way Symmetry of a circle
 *   3. Drawing single circles, concentric circles, or Olympic rings
 *
 * Compilation Commands:
 *   Linux:   g++ ass2_opengl.cpp -o ass2_opengl -lGL -lGLU -lglut
 *   Windows: g++ ass2_opengl.cpp -o ass2_opengl -lfreeglut -lopengl32 -lglu32
 *
 * Run (Linux):   ./ass2_opengl
 * Run (Windows): ass2_opengl.exe
 */

#include <GL/glut.h>

#include <iostream>
#include <vector>

using namespace std;

// Window dimensions
const int WINDOW_WIDTH = 640;
const int WINDOW_HEIGHT = 480;

// Pixel structure
struct Pixel {
    int x, y;
};

// Global list of pixels to draw
vector<Pixel> circlePixels;

/*
 * =====================================================================
 * 8-Way Symmetry Plotting
 * =====================================================================
 * A circle has 8-fold symmetry about the axes and lines y = x, y = -x.
 * For every computed point (x, y) in the first octant (where x <= y),
 * we plot 8 corresponding symmetric points around the center (xc, yc):
 *   Octant 1: (xc + x, yc + y)
 *   Octant 2: (xc - x, yc + y)
 *   Octant 3: (xc + x, yc - y)
 *   Octant 4: (xc - x, yc - y)
 *   Octant 5: (xc + y, yc + x)
 *   Octant 6: (xc - y, yc + x)
 *   Octant 7: (xc + y, yc - x)
 *   Octant 8: (xc - y, yc - x)
 */
void plot8SymmetricPoints(int xc, int yc, int x, int y) {
    circlePixels.push_back({xc + x, yc + y});
    circlePixels.push_back({xc - x, yc + y});
    circlePixels.push_back({xc + x, yc - y});
    circlePixels.push_back({xc - x, yc - y});

    circlePixels.push_back({xc + y, yc + x});
    circlePixels.push_back({xc - y, yc + x});
    circlePixels.push_back({xc + y, yc - x});
    circlePixels.push_back({xc - y, yc - x});
}

/*
 * =====================================================================
 * Bresenham's Circle Drawing Algorithm
 * =====================================================================
 * Theory:
 *   - Starts at the top of the circle: (x = 0, y = r).
 *   - Initial decision parameter: p = 3 - 2 * r  (or p = 1 - r).
 *   - At each step:
 *       If p < 0:
 *           Midpoint is INSIDE the circle.
 *           Choose East pixel: (x + 1, y).
 *           Update rule: p = p + 4 * x + 6
 *       If p >= 0:
 *           Midpoint is OUTSIDE the circle.
 *           Choose South-East pixel: (x + 1, y - 1).
 *           Update rule: p = p + 4 * (x - y) + 10
 *       Increment x by 1.
 *   - Stop when x > y (completes the 45-degree arc / first octant).
 */
void drawBresenhamCircle(int xc, int yc, int radius) {
    int x = 0;
    int y = radius;
    int p = 3 - 2 * radius; // Initial decision parameter

    while (x <= y) {
        plot8SymmetricPoints(xc, yc, x, y);

        if (p < 0) {
            p += 4 * x + 6;
        } else {
            p += 4 * (x - y) + 10;
            y--;
        }
        x++;
    }
}

// =====================================================================
// OpenGL Display Callback
// =====================================================================
void display() {
    glClear(GL_COLOR_BUFFER_BIT);

    // Draw coordinate axes passing through (0,0)
    glColor3f(0.35f, 0.35f, 0.35f); // subtle gray
    glBegin(GL_LINES);
        glVertex2i(-WINDOW_WIDTH / 2, 0); glVertex2i(WINDOW_WIDTH / 2, 0); // X-axis
        glVertex2i(0, -WINDOW_HEIGHT / 2); glVertex2i(0, WINDOW_HEIGHT / 2); // Y-axis
    glEnd();

    // Draw circle pixels
    glColor3f(0.2f, 0.8f, 1.0f); // Cyan
    glPointSize(2.0f);
    glBegin(GL_POINTS);
    for (const auto& pt : circlePixels) {
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
    cout << "  Assignment 2: Bresenham Circle Drawing        \n";
    cout << "=================================================\n";

    cout << "\nSelect Demo Mode:\n";
    cout << "  1. Single Circle (Default: Center (0, 0), Radius = 100)\n";
    cout << "  2. Concentric Circles (Radii = 50, 90, 130)\n";
    cout << "  3. Olympic Rings Pattern\n";
    cout << "  4. Custom Center & Radius\n";
    cout << "Enter choice (1-4): ";
    int choice;
    cin >> choice;

    if (choice == 1) {
        cout << "Drawing Single Circle (Center: 0, 0, Radius: 100)...\n";
        drawBresenhamCircle(0, 0, 100);
    } else if (choice == 2) {
        cout << "Drawing Concentric Circles at Center (0, 0)...\n";
        drawBresenhamCircle(0, 0, 40);
        drawBresenhamCircle(0, 0, 80);
        drawBresenhamCircle(0, 0, 120);
        drawBresenhamCircle(0, 0, 160);
    } else if (choice == 3) {
        cout << "Drawing Olympic Rings Pattern...\n";
        int r = 50;
        // Top 3 rings
        drawBresenhamCircle(-110, 30, r);
        drawBresenhamCircle(0, 30, r);
        drawBresenhamCircle(110, 30, r);
        // Bottom 2 interlocking rings
        drawBresenhamCircle(-55, -25, r);
        drawBresenhamCircle(55, -25, r);
    } else {
        int xc, yc, r;
        cout << "Enter Center (xc yc) relative to origin (0,0): ";
        cin >> xc >> yc;
        cout << "Enter Radius: ";
        cin >> r;
        drawBresenhamCircle(xc, yc, r);
    }

    cout << "Total pixels generated: " << circlePixels.size() << "\n";
    cout << "Opening OpenGL window...\n";

    // Initialize GLUT
    glutInit(&argc, argv);
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT);
    glutInitWindowPosition(150, 150);
    glutCreateWindow("Assignment 2: Bresenham Circle Drawing");

    // 2D orthographic projection centered at (0, 0)
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    gluOrtho2D(-WINDOW_WIDTH / 2, WINDOW_WIDTH / 2, -WINDOW_HEIGHT / 2, WINDOW_HEIGHT / 2);

    glutDisplayFunc(display);
    glutMainLoop();
    return 0;
}
