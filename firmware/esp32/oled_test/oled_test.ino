// OLED wiring: VCC->3V3, GND->GND, SDA->IO21, SCL->IO22
// If the screen stays blank, change OLED_ADDR to 0x3D and reflash.

#include <Wire.h>
#include <string.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define OLED_ADDR 0x3C

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

unsigned long startTime = 0;
bool wifiPhase = false;

void showWelcome() {
  display.clearDisplay();
  display.setTextSize(2);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.print("SMART");
  display.setCursor(0, 18);
  display.print("BIN");
  display.setTextSize(1);
  display.setCursor(0, 44);
  display.print("ESP32 + SSD1306 OK");
  display.display();
}

void scrollWelcome() {
  const char *msg = "Welcome to SmartBin IoT";
  int textWidth = strlen(msg) * 16;
  for (int x = 0; x >= -textWidth; x -= 2) {
    display.clearDisplay();
    display.setTextSize(2);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(x, 8);
    display.print(msg);
    display.setTextSize(1);
    display.setCursor(0, 34);
    display.print("fill-level monitoring system");
    display.display();
    delay(40);
  }
}

void showRuler() {
  display.clearDisplay();
  display.fillRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, SSD1306_WHITE);
  display.fillRect(2, 2, SCREEN_WIDTH - 4, SCREEN_HEIGHT - 4, SSD1306_BLACK);
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(6, 6);
  display.print("OLED DISPLAY");
  display.setCursor(6, 18);
  display.print("TEST 100% OK");
  display.setCursor(6, 30);
  display.print("128 x 64");
  for (int x = 0; x < SCREEN_WIDTH; x += 8) {
    display.drawLine(x, 40, x, 48, SSD1306_WHITE);
  }
  display.setCursor(6, 52);
  display.print("|__|__|__|__|");
  display.display();
}

void setup() {
  Serial.begin(115200);
  delay(200);

  Wire.begin(21, 22);
  Serial.println("Scanning I2C bus...");
  uint8_t found = 0;
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.print("  device found at 0x");
      if (addr < 16) Serial.print("0");
      Serial.println(addr, HEX);
      found++;
    }
  }
  if (found == 0) Serial.println("  no I2C device found - check SDA/SCL wiring");
  Serial.println();

  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("SSD1306 init FAILED at 0x3C - try 0x3D");
    while (true) delay(1000);
  }
  Serial.println("SSD1306 init OK");
  startTime = millis();

  display.clearDisplay();
  display.fillScreen(SSD1306_WHITE);
  display.display();
  delay(1200);

  showWelcome();
  delay(2500);

  showRuler();
  delay(2500);

  scrollWelcome();

  display.clearDisplay();
  display.setTextSize(2);
  display.setCursor(0, 0);
  display.print("WELCOME");
  display.setTextSize(1);
  display.setCursor(0, 20);
  display.print("to SmartBin!");
  display.setCursor(0, 36);
  display.print("Uptime ");
  display.print((millis() - startTime) / 1000);
  display.print("s");
  display.display();
}

void loop() {
  delay(1000);
}
