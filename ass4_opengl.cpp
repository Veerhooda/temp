/*
 * Assignment 4: Cohen-Sutherland Line & Polygon Clipping
 * --------------------------------------------------------
 * Demonstrates:
 *   1. Cohen-Sutherland Line Clipping Algorithm
 *   2. 4-bit Region Outcodes (Top, Bottom, Right, Left)
 *   3. Trivial Acceptance & Trivial Rejection tests
 *   4. Edge intersection calculations
 *   5. Window-to-Viewport coordinate transformation
 *   6. Polygon clipping by clipping all bounding edges
 *
 * Compilation Commands:
 *   Linux:   g++ ass4_opengl.cpp -o ass4_opengl -lGL -lGLU -lglut
 *   Windows: g++ ass4_opengl.cpp -o ass4_opengl -lfreeglut -lopengl32 -lglu32
 *
 * Run (Linux):   ./ass4_opengl
 * Run (Windows): ass4_opengl.exe
 */

#include <GL/glut.h>

#include <iostream>
#include <vector>

using namespace std;

// Screen dimensions
const int WINDOW_WIDTH  = 800;
const int WINDOW_HEIGHT = 600;

// 1. Clipping Window boundaries (World coordinates)
const float WX_MIN = 120.0f, WY_MIN = 150.0f;
const float WX_MAX = 340.0f, WY_MAX = 420.0f;

// 2. Viewport boundaries (Screen display area)
const float VX_MIN = 460.0f, VY_MIN = 150.0f;
const float VX_MAX = 680.0f, VY_MAX = 420.0f;

// Standard 4-bit Outcodes (TBRL / LRBT)
const int LEFT   = 1; // Bit 0: 0001
const int RIGHT  = 2; // Bit 1: 0010
const int BOTTOM = 4; // Bit 2: 0100
const int TOP    = 8; // Bit 3: 1000

// 2D Point structure
struct Point {
    float x, y;
};

// Polygon representation
vector<Point> originalPolygon;
vector<pair<Point, Point>> clippedEdges;
vector<pair<Point, Point>> viewportEdges;

bool isClipped = false;

/*
 * =====================================================================
 * Compute 4-bit Region Outcode
 * =====================================================================
 * Assigns a 4-bit code depending on where (x, y) lies relative to window:
 *   - Left:   x < WX_MIN
 *   - Right:  x > WX_MAX
 *   - Bottom: y < WY_MIN
 *   - Top:    y > WY_MAX
 * If point is inside the window, outcode is 0000 (0).
 */
int computeOutCode(float x, float y) {
    int code = 0;
    if (x < WX_MIN) code |= LEFT;
    if (x > WX_MAX) code |= RIGHT;
    if (y < WY_MIN) code |= BOTTOM;
    if (y > WY_MAX) code |= TOP;
    return code;
}

/*
 * =====================================================================
 * Window-to-Viewport Coordinate Mapping
 * =====================================================================
 * Formula:
 *   Xv = VX_MIN + (Xw - WX_MIN) * (VX_MAX - VX_MIN) / (WX_MAX - WX_MIN)
 *   Yv = VY_MIN + (Yw - WY_MIN) * (VY_MAX - VY_MIN) / (WY_MAX - WY_MIN)
 */
Point mapToViewport(Point p) {
    Point vp;
    float sx = (VX_MAX - VX_MIN) / (WX_MAX - WX_MIN);
    float sy = (VY_MAX - VY_MIN) / (WY_MAX - WY_MIN);
    vp.x = VX_MIN + (p.x - WX_MIN) * sx;
    vp.y = VY_MIN + (p.y - WY_MIN) * sy;
    return vp;
}

/*
 * =====================================================================
 * Cohen-Sutherland Line Clipping Algorithm
 * =====================================================================
 * Theory:
 *   1. Calculate outcodes for endpoints p1 and p2.
 *   2. Trivial Accept: (code1 | code2) == 0 -> both inside window.
 *   3. Trivial Reject: (code1 & code2) != 0 -> both share an outside region.
 *   4. Otherwise: Clip against boundary planes one by one.
 */
void clipLine(Point p1, Point p2) {
    int code1 = computeOutCode(p1.x, p1.y);
    int code2 = computeOutCode(p2.x, p2.y);
    bool accept = false;

    while (true) {
        // Trivial Accept: both endpoints have code 0000
        if ((code1 | code2) == 0) {
            accept = true;
            break;
        }
        // Trivial Reject: both endpoints share an outside edge
        if ((code1 & code2) != 0) {
            break;
        }

        // Pick an endpoint that is outside the clipping window
        int outsideCode = (code1 != 0) ? code1 : code2;
        float x = 0, y = 0;
        float dx = p2.x - p1.x;
        float dy = p2.y - p1.y;

        // Calculate intersection with window boundary using slope
        if (outsideCode & TOP) {
            // Intersect with y = WY_MAX
            x = p1.x + dx * (WY_MAX - p1.y) / dy;
            y = WY_MAX;
        } else if (outsideCode & BOTTOM) {
            // Intersect with y = WY_MIN
            x = p1.x + dx * (WY_MIN - p1.y) / dy;
            y = WY_MIN;
        } else if (outsideCode & RIGHT) {
            // Intersect with x = WX_MAX
            y = p1.y + dy * (WX_MAX - p1.x) / dx;
            x = WX_MAX;
        } else if (outsideCode & LEFT) {
            // Intersect with x = WX_MIN
            y = p1.y + dy * (WX_MIN - p1.x) / dx;
            x = WX_MIN;
        }

        // Update the clipped point and recompute its outcode
        if (outsideCode == code1) {
            p1.x = x;
            p1.y = y;
            code1 = computeOutCode(p1.x, p1.y);
        } else {
            p2.x = x;
            p2.y = y;
            code2 = computeOutCode(p2.x, p2.y);
        }
    }

    if (accept) {
        clippedEdges.push_back({p1, p2});
        viewportEdges.push_back({mapToViewport(p1), mapToViewport(p2)});
    }
}

// Perform clipping on all edges of the polygon
void performPolygonClipping() {
    clippedEdges.clear();
    viewportEdges.clear();
    int n = originalPolygon.size();

    for (int i = 0; i < n; i++) {
        Point p1 = originalPolygon[i];
        Point p2 = originalPolygon[(i + 1) % n];
        clipLine(p1, p2);
    }
    isClipped = true;
    cout << "\nClipping Complete! " << clippedEdges.size() << " visible edge segment(s) inside window.\n";
}

// =====================================================================
// Keyboard Interaction (Press 'C' to clip, 'R' to reset)
// =====================================================================
void keyboard(unsigned char key, int x, int y) {
    if (key == 'c' || key == 'C') {
        performPolygonClipping();
        glutPostRedisplay();
    } else if (key == 'r' || key == 'R') {
        isClipped = false;
        clippedEdges.clear();
        viewportEdges.clear();
        cout << "\nReset to unclipped polygon.\n";
        glutPostRedisplay();
    }
}

// =====================================================================
// OpenGL Display Callback
// =====================================================================
void display() {
    glClear(GL_COLOR_BUFFER_BIT);

    // 1. Draw Clipping Window (Red Box)
    glColor3f(1.0f, 0.2f, 0.2f);
    glLineWidth(2.0f);
    glBegin(GL_LINE_LOOP);
        glVertex2f(WX_MIN, WY_MIN);
        glVertex2f(WX_MAX, WY_MIN);
        glVertex2f(WX_MAX, WY_MAX);
        glVertex2f(WX_MIN, WY_MAX);
    glEnd();

    // 2. Draw Viewport (Blue Box)
    glColor3f(0.2f, 0.5f, 1.0f);
    glBegin(GL_LINE_LOOP);
        glVertex2f(VX_MIN, VY_MIN);
        glVertex2f(VX_MAX, VY_MIN);
        glVertex2f(VX_MAX, VY_MAX);
        glVertex2f(VX_MIN, VY_MAX);
    glEnd();

    // 3. Draw Original Polygon (Yellow) before clipping
    if (!isClipped && originalPolygon.size() > 1) {
        glColor3f(1.0f, 1.0f, 0.0f); // Yellow
        glLineWidth(1.5f);
        glBegin(GL_LINE_LOOP);
        for (const auto& pt : originalPolygon) {
            glVertex2f(pt.x, pt.y);
        }
        glEnd();
    }

    // 4. Draw Clipped Results
    if (isClipped) {
        // Clipped lines inside window (Green)
        glColor3f(0.2f, 1.0f, 0.2f);
        glLineWidth(3.0f);
        glBegin(GL_LINES);
        for (const auto& edge : clippedEdges) {
            glVertex2f(edge.first.x, edge.first.y);
            glVertex2f(edge.second.x, edge.second.y);
        }
        glEnd();

        // Viewport-mapped lines (Cyan)
        glColor3f(0.2f, 1.0f, 1.0f);
        glLineWidth(3.0f);
        glBegin(GL_LINES);
        for (const auto& edge : viewportEdges) {
            glVertex2f(edge.first.x, edge.first.y);
            glVertex2f(edge.second.x, edge.second.y);
        }
        glEnd();
    }

    glFlush();
}

// =====================================================================
// Main Function with User Menu
// =====================================================================
int main(int argc, char** argv) {
    cout << "=======================================================\n";
    cout << "  Assignment 4: Cohen-Sutherland Polygon Clipping     \n";
    cout << "=======================================================\n";

    cout << "\nWindow (Red Box):     [" << WX_MIN << ", " << WY_MIN << "] to [" << WX_MAX << ", " << WY_MAX << "]\n";
    cout << "Viewport (Blue Box):  [" << VX_MIN << ", " << VY_MIN << "] to [" << VX_MAX << ", " << VY_MAX << "]\n";

    cout << "\nSelect Polygon Input:\n";
    cout << "  1. Use Default Test Polygon (Quadrilateral spanning window borders)\n";
    cout << "  2. Enter Custom Polygon Vertices\n";
    cout << "Enter choice (1 or 2): ";
    int choice;
    cin >> choice;

    if (choice == 1) {
        // Preset polygon overlapping all 4 boundaries of the window
        originalPolygon = {
            {80, 200},   // Left outside
            {230, 480},  // Top outside
            {380, 320},  // Right outside
            {200, 100}   // Bottom outside
        };
        cout << "Loaded preset 4-vertex polygon.\n";
    } else {
        int numVertices;
        cout << "Enter number of vertices (>= 3): ";
        cin >> numVertices;
        for (int i = 0; i < numVertices; i++) {
            Point p;
            cout << "Vertex " << (i + 1) << " (x y): ";
            cin >> p.x >> p.y;
            originalPolygon.push_back(p);
        }
    }

    cout << "\n-------------------------------------------------------\n";
    cout << "CONTROLS IN GRAPHICS WINDOW:\n";
    cout << "  Press 'C' : Perform Cohen-Sutherland Clipping\n";
    cout << "  Press 'R' : Reset to original polygon\n";
    cout << "-------------------------------------------------------\n";

    glutInit(&argc, argv);
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT);
    glutInitWindowPosition(100, 100);
    glutCreateWindow("Assignment 4: Cohen-Sutherland Polygon Clipping");

    // Standard Cartesian coordinates: (0,0) at bottom-left, Y points upward
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT);

    glutDisplayFunc(display);
    glutKeyboardFunc(keyboard);
    glutMainLoop();
    return 0;
}
