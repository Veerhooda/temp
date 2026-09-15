/*
 * Assignment 7: Interactive Animation using C++ OOP
 * ----------------------------------------------------
 * Demonstrates:
 *   1. Object-Oriented Programming (OOP) in Computer Graphics:
 *        - Abstract Base Class (GraphicObject)
 *        - Pure Virtual Functions (draw(), update())
 *        - Inheritance & Runtime Polymorphism (Base class pointer -> Derived instances)
 *   2. Bouncing Ball with Gravity, Velocity, and Ground Damping physics
 *   3. Moving Car with Multi-part Composite Rendering
 *   4. Double-buffered smooth 60 FPS animation using glutTimerFunc
 *   5. Keyboard interactions (Space to Pause, '1' / '2' to switch, 'R' to reset)
 *
 * Compilation Commands:
 *   Linux:   g++ ass7_opengl.cpp -o ass7_opengl -lGL -lGLU -lglut -lm
 *   Windows: g++ ass7_opengl.cpp -o ass7_opengl -lfreeglut -lopengl32 -lglu32
 *
 * Run (Linux):   ./ass7_opengl
 * Run (Windows): ass7_opengl.exe
 */

#include <GL/glut.h>

#include <iostream>
#include <cmath>

using namespace std;

// Screen dimensions
const int WINDOW_WIDTH  = 640;
const int WINDOW_HEIGHT = 480;
const float PI = 3.14159265358979323846f;
const float GROUND_Y = 80.0f; // Height of ground line in Cartesian coords

bool isPaused = false;

/*
 * =====================================================================
 * Helper: Draw a solid filled circle or outline circle
 * =====================================================================
 */
void drawCircle(float cx, float cy, float radius, bool filled = false) {
    if (filled) glBegin(GL_POLYGON);
    else        glBegin(GL_LINE_LOOP);

    for (int i = 0; i < 360; i += 10) {
        float rad = i * PI / 180.0f;
        glVertex2f(cx + radius * cos(rad), cy + radius * sin(rad));
    }
    glEnd();
}

/*
 * =====================================================================
 * OOP BASE CLASS: GraphicObject (Abstract Class)
 * =====================================================================
 * Demonstrates:
 *   - Encapsulation of common (x, y) coordinates
 *   - Pure Virtual Functions: force derived classes to implement draw() & update()
 *   - Virtual Destructor for safe polymorphic cleanup
 */
class GraphicObject {
protected:
    float x, y;
public:
    GraphicObject(float initX = 0, float initY = 0) : x(initX), y(initY) {}
    virtual ~GraphicObject() {}

    // Pure virtual functions (must be overridden by subclasses)
    virtual void draw() = 0;
    virtual void update() = 0;
    virtual void reset() = 0;
};

/*
 * =====================================================================
 * DERIVED CLASS 1: BouncingBall
 * =====================================================================
 * Simulates a ball bouncing under gravity:
 *   - Gravity accelerates downward velocity: vy -= gravity
 *   - Damping: Upon hitting the ground, velocity reverses and loses 15% energy
 *   - Bounces off left and right window borders
 */
class BouncingBall : public GraphicObject {
private:
    float vx, vy;
    float gravity;
    float damping;
    float radius;
public:
    BouncingBall() : GraphicObject(120.0f, 350.0f) {
        vx = 2.5f;
        vy = 0.0f;
        gravity = 0.4f;
        damping = 0.85f; // Retains 85% energy after collision
        radius = 22.0f;
    }

    void reset() override {
        x = 120.0f;
        y = 350.0f;
        vx = 2.5f;
        vy = 0.0f;
    }

    void draw() override {
        // Draw Ground Line
        glColor3f(0.5f, 0.3f, 0.1f);
        glLineWidth(3.0f);
        glBegin(GL_LINES);
            glVertex2f(0, GROUND_Y); glVertex2f(WINDOW_WIDTH, GROUND_Y);
        glEnd();

        // Draw Bouncing Ball (Yellow with orange rim)
        glColor3f(1.0f, 0.85f, 0.1f); // Yellow
        drawCircle(x, y, radius, true);

        glColor3f(0.9f, 0.4f, 0.0f); // Orange border
        glLineWidth(2.0f);
        drawCircle(x, y, radius, false);
    }

    void update() override {
        // Apply gravity downward
        vy -= gravity;

        // Update positions
        x += vx;
        y += vy;

        // Ground collision
        if (y - radius <= GROUND_Y) {
            y = GROUND_Y + radius;
            vy = -vy * damping; // Reverse and dampen velocity
        }

        // Left and Right wall collisions
        if (x + radius >= WINDOW_WIDTH) {
            x = WINDOW_WIDTH - radius;
            vx = -vx;
        } else if (x - radius <= 0) {
            x = radius;
            vx = -vx;
        }
    }
};

/*
 * =====================================================================
 * DERIVED CLASS 2: MovingCar
 * =====================================================================
 * Renders a composite moving car:
 *   - Lower body chassis
 *   - Upper cabin and tinted windows
 *   - Rotating wheels with spokes
 *   - Glowing yellow headlights
 */
class MovingCar : public GraphicObject {
private:
    float speed;
    float carWidth, carHeight;
    float wheelRadius;
    float wheelAngle;
public:
    MovingCar() : GraphicObject(-120.0f, GROUND_Y + 12.0f) {
        speed = 3.0f;
        carWidth = 130.0f;
        carHeight = 35.0f;
        wheelRadius = 14.0f;
        wheelAngle = 0.0f;
    }

    void reset() override {
        x = -120.0f;
        y = GROUND_Y + 12.0f;
    }

    void draw() override {
        // Ground line
        glColor3f(0.4f, 0.4f, 0.4f);
        glLineWidth(3.0f);
        glBegin(GL_LINES);
            glVertex2f(0, GROUND_Y); glVertex2f(WINDOW_WIDTH, GROUND_Y);
        glEnd();

        float cx = x;
        float cy = y;

        // 1. Lower Body Chassis (Red)
        glColor3f(0.9f, 0.15f, 0.15f);
        glBegin(GL_POLYGON);
            glVertex2f(cx, cy);
            glVertex2f(cx + carWidth, cy);
            glVertex2f(cx + carWidth, cy + carHeight);
            glVertex2f(cx, cy + carHeight);
        glEnd();

        // 2. Upper Cabin (Darker Red)
        glColor3f(0.75f, 0.1f, 0.1f);
        glBegin(GL_POLYGON);
            glVertex2f(cx + 25.0f, cy + carHeight);
            glVertex2f(cx + 100.0f, cy + carHeight);
            glVertex2f(cx + 85.0f, cy + carHeight + 28.0f);
            glVertex2f(cx + 35.0f, cy + carHeight + 28.0f);
        glEnd();

        // 3. Windows (Light Blue)
        glColor3f(0.6f, 0.85f, 1.0f);
        // Front Window
        glBegin(GL_POLYGON);
            glVertex2f(cx + 38.0f, cy + carHeight + 3.0f);
            glVertex2f(cx + 58.0f, cy + carHeight + 3.0f);
            glVertex2f(cx + 58.0f, cy + carHeight + 24.0f);
            glVertex2f(cx + 42.0f, cy + carHeight + 24.0f);
        glEnd();
        // Rear Window
        glBegin(GL_POLYGON);
            glVertex2f(cx + 64.0f, cy + carHeight + 3.0f);
            glVertex2f(cx + 94.0f, cy + carHeight + 3.0f);
            glVertex2f(cx + 82.0f, cy + carHeight + 24.0f);
            glVertex2f(cx + 64.0f, cy + carHeight + 24.0f);
        glEnd();

        // 4. Wheels (Dark Gray tires with spoke lines)
        float frontWheelX = cx + 28.0f;
        float rearWheelX  = cx + 102.0f;
        float wheelY      = cy;

        for (float wx : {frontWheelX, rearWheelX}) {
            // Tire
            glColor3f(0.15f, 0.15f, 0.15f);
            drawCircle(wx, wheelY, wheelRadius, true);
            // Rim
            glColor3f(0.8f, 0.8f, 0.8f);
            drawCircle(wx, wheelY, wheelRadius * 0.5f, true);
            // Rotating spoke
            glColor3f(0.2f, 0.2f, 0.2f);
            glBegin(GL_LINES);
                float rad = wheelAngle * PI / 180.0f;
                glVertex2f(wx - wheelRadius * cos(rad), wheelY - wheelRadius * sin(rad));
                glVertex2f(wx + wheelRadius * cos(rad), wheelY + wheelRadius * sin(rad));
            glEnd();
        }

        // 5. Headlight (Yellow)
        glColor3f(1.0f, 1.0f, 0.2f);
        drawCircle(cx + carWidth, cy + carHeight * 0.6f, 5.0f, true);
    }

    void update() override {
        x += speed;
        wheelAngle -= 8.0f; // Rotate wheels as car moves forward

        // Wrap around when car moves off-screen to the right
        if (x > WINDOW_WIDTH + 20.0f) {
            x = -carWidth - 20.0f;
        }
    }
};

// =====================================================================
// Global Polymorphic Pointer to current active object
// =====================================================================
GraphicObject* currentObject = nullptr;

// =====================================================================
// OpenGL Display Callback
// =====================================================================
void display() {
    glClear(GL_COLOR_BUFFER_BIT);

    if (currentObject) {
        currentObject->draw();
    }

    // Swap front and back buffers for flicker-free rendering
    glutSwapBuffers();
}

// =====================================================================
// 60 FPS Animation Timer Callback (16 ms ~ 60 FPS)
// =====================================================================
void timer(int) {
    if (!isPaused && currentObject) {
        currentObject->update();
        glutPostRedisplay();
    }
    glutTimerFunc(16, timer, 0);
}

// =====================================================================
// Keyboard Interaction
// =====================================================================
void keyboard(unsigned char key, int, int) {
    if (key == ' ') {
        isPaused = !isPaused;
        cout << (isPaused ? "Animation PAUSED\n" : "Animation RESUMED\n");
    } else if (key == '1') {
        delete currentObject;
        currentObject = new BouncingBall();
        cout << "Switched to: Bouncing Ball\n";
    } else if (key == '2') {
        delete currentObject;
        currentObject = new MovingCar();
        cout << "Switched to: Moving Car\n";
    } else if (key == 'r' || key == 'R') {
        if (currentObject) currentObject->reset();
        cout << "Object position reset.\n";
    }
}

// =====================================================================
// Main Function with User Menu
// =====================================================================
int main(int argc, char** argv) {
    cout << "=======================================================\n";
    cout << "  Assignment 7: Interactive OOP Graphics Demo         \n";
    cout << "=======================================================\n";

    cout << "\nChoose Demo Object:\n";
    cout << "  1. Bouncing Ball (Simulates gravity & collision damping)\n";
    cout << "  2. Moving Car    (Composite multi-part object rendering)\n";
    cout << "Enter choice (1 or 2): ";
    int choice;
    cin >> choice;

    // Runtime Polymorphism: Instantiate chosen derived object
    if (choice == 2) {
        currentObject = new MovingCar();
    } else {
        currentObject = new BouncingBall();
    }

    cout << "\n-------------------------------------------------------\n";
    cout << "INTERACTIVE KEYBOARD CONTROLS:\n";
    cout << "  [SPACEBAR] : Pause / Resume animation\n";
    cout << "  [1]        : Switch to Bouncing Ball\n";
    cout << "  [2]        : Switch to Moving Car\n";
    cout << "  [R]        : Reset position\n";
    cout << "-------------------------------------------------------\n";

    glutInit(&argc, argv);
    // Double buffer mode for smooth rendering without flicker
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB);
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT);
    glutInitWindowPosition(100, 100);
    glutCreateWindow("Assignment 7: Interactive Graphics (OOP)");

    // Standard Cartesian coordinates: (0,0) at bottom-left
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT);

    glutDisplayFunc(display);
    glutTimerFunc(16, timer, 0);
    glutKeyboardFunc(keyboard);

    glutMainLoop();

    delete currentObject;
    return 0;
}
