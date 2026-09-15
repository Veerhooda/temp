/*
 * Assignment 3: Polygon Filling (Flood Fill & Boundary Fill)
 * -----------------------------------------------------------
 * Demonstrates:
 *   1. Flood Fill Algorithm (Seed Fill replacing background color)
 *   2. Boundary Fill Algorithm (Seed Fill stopping at a boundary color)
 *   3. 4-Connected neighbor traversal
 *   4. Safe Stack-based iteration (avoids recursion stack overflow)
 *   5. Interactive mouse click to fill
 *
 * Compilation Commands:
 *   Linux:   g++ ass3_opengl.cpp -o ass3_opengl -lGL -lGLU -lglut
 *   Windows: g++ ass3_opengl.cpp -o ass3_opengl -lfreeglut -lopengl32 -lglu32
 *
 * Run (Linux):   ./ass3_opengl
 * Run (Windows): ass3_opengl.exe
 */

#include <GL/glut.h>

#include <iostream>
#include <vector>
#include <stack>

using namespace std;

// Window dimensions
const int WINDOW_WIDTH = 640;
const int WINDOW_HEIGHT = 480;

// Pixel color state codes for our simple grid:
// 0 = Background (Black)
// 1 = Boundary (White)
// 2 = Filled Area (Red)
const int COLOR_BACKGROUND = 0;
const int COLOR_BOUNDARY   = 1;
const int COLOR_FILL       = 2;

// 2D grid storing state of each pixel on the screen
int pixelGrid[WINDOW_WIDTH][WINDOW_HEIGHT];

// List of all filled pixels to render quickly in OpenGL
vector<pair<int, int>> filledPixels;

int fillMode = 1; // 1 = Flood Fill, 2 = Boundary Fill

// Boundary rectangle coordinates
const int RECT_X1 = 180, RECT_Y1 = 140;
const int RECT_X2 = 460, RECT_Y2 = 340;

// Setup initial boundary shape on the grid
void initializeShape() {
    // Clear grid to background
    for (int x = 0; x < WINDOW_WIDTH; x++) {
        for (int y = 0; y < WINDOW_HEIGHT; y++) {
            pixelGrid[x][y] = COLOR_BACKGROUND;
        }
    }
    filledPixels.clear();

    // Draw top and bottom horizontal boundaries
    for (int x = RECT_X1; x <= RECT_X2; x++) {
        pixelGrid[x][RECT_Y1] = COLOR_BOUNDARY;
        pixelGrid[x][RECT_Y2] = COLOR_BOUNDARY;
    }

    // Draw left and right vertical boundaries
    for (int y = RECT_Y1; y <= RECT_Y2; y++) {
        pixelGrid[RECT_X1][y] = COLOR_BOUNDARY;
        pixelGrid[RECT_X2][y] = COLOR_BOUNDARY;
    }
}

/*
 * =====================================================================
 * 1. Flood Fill Algorithm (Iterative using Stack)
 * =====================================================================
 * Theory:
 *   - Starts from a seed point (seedX, seedY).
 *   - Reads the old target color (e.g. COLOR_BACKGROUND).
 *   - Replaces the target color with the new fill color (COLOR_FILL).
 *   - Traverses 4-connected neighbors: (x+1, y), (x-1, y), (x, y+1), (x, y-1).
 *   - NOTE: We use an explicit std::stack instead of recursion to prevent
 *     program crashes due to stack overflow on large shapes!
 */
void floodFill(int seedX, int seedY, int targetColor, int newColor) {
    // If seed already has the new color, nothing to do
    if (pixelGrid[seedX][seedY] != targetColor || targetColor == newColor) return;

    stack<pair<int, int>> pixelStack;
    pixelStack.push({seedX, seedY});

    // Mark as filled immediately to prevent pushing duplicate coordinates
    pixelGrid[seedX][seedY] = newColor;
    filledPixels.push_back({seedX, seedY});

    while (!pixelStack.empty()) {
        auto [cx, cy] = pixelStack.top();
        pixelStack.pop();

        // Check 4-connected neighbors
        int dx[4] = {1, -1, 0, 0};
        int dy[4] = {0, 0, 1, -1};

        for (int i = 0; i < 4; i++) {
            int nx = cx + dx[i];
            int ny = cy + dy[i];

            // Ensure neighbor is within screen bounds
            if (nx >= 0 && nx < WINDOW_WIDTH && ny >= 0 && ny < WINDOW_HEIGHT) {
                // If neighbor matches target color, fill and push to stack
                if (pixelGrid[nx][ny] == targetColor) {
                    pixelGrid[nx][ny] = newColor;
                    filledPixels.push_back({nx, ny});
                    pixelStack.push({nx, ny});
                }
            }
        }
    }
}

/*
 * =====================================================================
 * 2. Boundary Fill Algorithm (Iterative using Stack)
 * =====================================================================
 * Theory:
 *   - Starts from a seed point (seedX, seedY).
 *   - Fills until it hits a specified boundary color (COLOR_BOUNDARY).
 *   - Condition to color a pixel:
 *       pixel != boundaryColor AND pixel != newColor
 *   - Traverses 4-connected neighbors in all directions.
 */
void boundaryFill(int seedX, int seedY, int boundaryColor, int newColor) {
    if (pixelGrid[seedX][seedY] == boundaryColor || pixelGrid[seedX][seedY] == newColor) return;

    stack<pair<int, int>> pixelStack;
    pixelStack.push({seedX, seedY});

    pixelGrid[seedX][seedY] = newColor;
    filledPixels.push_back({seedX, seedY});

    while (!pixelStack.empty()) {
        auto [cx, cy] = pixelStack.top();
        pixelStack.pop();

        int dx[4] = {1, -1, 0, 0};
        int dy[4] = {0, 0, 1, -1};

        for (int i = 0; i < 4; i++) {
            int nx = cx + dx[i];
            int ny = cy + dy[i];

            if (nx >= 0 && nx < WINDOW_WIDTH && ny >= 0 && ny < WINDOW_HEIGHT) {
                // Color if it is NOT the boundary AND NOT already filled
                if (pixelGrid[nx][ny] != boundaryColor && pixelGrid[nx][ny] != newColor) {
                    pixelGrid[nx][ny] = newColor;
                    filledPixels.push_back({nx, ny});
                    pixelStack.push({nx, ny});
                }
            }
        }
    }
}

// =====================================================================
// Mouse Interaction Callback
// =====================================================================
void mouseClick(int button, int state, int mouseX, int mouseY) {
    // When left mouse button is pressed down
    if (button == GLUT_LEFT_BUTTON && state == GLUT_DOWN) {
        cout << "Seed clicked at: (" << mouseX << ", " << mouseY << ")\n";

        if (fillMode == 1) {
            cout << "Applying Flood Fill...\n";
            floodFill(mouseX, mouseY, COLOR_BACKGROUND, COLOR_FILL);
        } else {
            cout << "Applying Boundary Fill...\n";
            boundaryFill(mouseX, mouseY, COLOR_BOUNDARY, COLOR_FILL);
        }

        // Request OpenGL to redraw the window with the newly filled pixels
        glutPostRedisplay();
    }
}

// =====================================================================
// Keyboard Interaction Callback (Press 'R' to reset)
// =====================================================================
void keyboard(unsigned char key, int x, int y) {
    if (key == 'r' || key == 'R') {
        cout << "Resetting canvas...\n";
        initializeShape();
        glutPostRedisplay();
    }
}

// =====================================================================
// OpenGL Display Callback
// =====================================================================
void display() {
    glClear(GL_COLOR_BUFFER_BIT);

    // 1. Draw boundary box in White
    glColor3f(1.0f, 1.0f, 1.0f);
    glLineWidth(2.0f);
    glBegin(GL_LINE_LOOP);
        glVertex2i(RECT_X1, RECT_Y1);
        glVertex2i(RECT_X2, RECT_Y1);
        glVertex2i(RECT_X2, RECT_Y2);
        glVertex2i(RECT_X1, RECT_Y2);
    glEnd();

    // 2. Draw all filled pixels in Red
    glColor3f(1.0f, 0.2f, 0.2f); // Vibrant Red
    glPointSize(1.0f);
    glBegin(GL_POINTS);
    for (const auto& pt : filledPixels) {
        glVertex2i(pt.first, pt.second);
    }
    glEnd();

    glFlush();
}

// =====================================================================
// Main Function with User Menu
// =====================================================================
int main(int argc, char** argv) {
    cout << "=================================================\n";
    cout << "  Assignment 3: Polygon Filling Algorithms      \n";
    cout << "=================================================\n";

    cout << "\nChoose Filling Algorithm:\n";
    cout << "  1. Flood Fill    (Replaces interior background color)\n";
    cout << "  2. Boundary Fill (Fills outward until white border)\n";
    cout << "Enter choice (1 or 2): ";
    cin >> fillMode;

    cout << "\n-------------------------------------------------\n";
    cout << "INSTRUCTIONS:\n";
    cout << "  - Click LEFT MOUSE BUTTON inside the white box to fill it.\n";
    cout << "  - Press 'R' on keyboard to reset the canvas.\n";
    cout << "-------------------------------------------------\n";

    initializeShape();

    // Initialize GLUT
    glutInit(&argc, argv);
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT);
    glutInitWindowPosition(100, 100);
    glutCreateWindow("Assignment 3: Flood Fill & Boundary Fill");

    // In 2D screen coordinate space:
    // (0,0) is at top-left, matching GLUT mouse coordinates directly
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    gluOrtho2D(0, WINDOW_WIDTH, WINDOW_HEIGHT, 0);

    glutDisplayFunc(display);
    glutMouseFunc(mouseClick);
    glutKeyboardFunc(keyboard);
    glutMainLoop();
    return 0;
}
