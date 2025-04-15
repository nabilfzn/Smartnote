#include <driver/i2s.h>
#include <FS.h>
#include <SD.h>
#include <SPI.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include <ArduinoJson.h>

// WiFi configuration
const char* ssid = "WIFI";       // Change to your WiFi SSID
const char* password = "PASSWIFI"; // Change to your WiFi password
const char* serverUrl = "IPADDR"; // Change to your server IP/hostname

// Create web server
WebServer server(80);

// I2S configurations
#define I2S_WS 15       // Word Select pin (also called LRC or LRCLK)
#define I2S_SD 32       // Serial Data pin (also called DOUT or DATA)
#define I2S_SCK 14      // Serial Clock pin (also called BCLK)
#define I2S_PORT I2S_NUM_0

// SD Card pins for SPI
#define SD_CS 5         // SD Card chip select
#define SD_SCK 18       // SD Card SPI clock
#define SD_MISO 19      // SD Card SPI MISO
#define SD_MOSI 23      // SD Card SPI MOSI

// Recording parameters
#define SAMPLE_RATE 16000           // Audio sample rate in Hz
#define SAMPLE_BITS 16              // Sample bits
#define CHANNELS 1                  // Number of channels (1 for mono)
#define BUFFER_SIZE 512             // DMA buffer size

// Test parameters
#define MIC_TEST_DURATION_MS 2000   // Duration for the microphone test in milliseconds
#define MIC_AMPLITUDE_THRESHOLD 500 // Minimum amplitude to consider microphone working

// Global variables
bool isRecording = false;
File audioFile;
unsigned long recordingStartTime = 0;
int fileCounter = 0;
bool sdCardOK = false;
bool microphoneOK = false;
bool wifiConnected = false;
String currentFilename = "";
unsigned long recordingDuration = 0;

// WAV file header structure
struct wav_header_t {
  char riff[4] = {'R', 'I', 'F', 'F'};
  uint32_t chunk_size;
  char wave[4] = {'W', 'A', 'V', 'E'};
  char fmt[4] = {'f', 'm', 't', ' '};
  uint32_t fmt_size = 16;
  uint16_t audio_format = 1;  // PCM
  uint16_t num_channels = CHANNELS;
  uint32_t sample_rate = SAMPLE_RATE;
  uint32_t byte_rate = SAMPLE_RATE * CHANNELS * (SAMPLE_BITS / 8);
  uint16_t block_align = CHANNELS * (SAMPLE_BITS / 8);
  uint16_t bits_per_sample = SAMPLE_BITS;
  char data[4] = {'d', 'a', 't', 'a'};
  uint32_t data_size;
};

void setup() {
  Serial.begin(115200);
  delay(1000); // Give time for Serial Monitor to open
  
  Serial.println("\n\n----- ESP32 INMP441 Recording to SD Card with WiFi Upload -----");
  
  // Run hardware diagnostics
  runDiagnostics();
  
  // Connect to WiFi
  setupWiFi();
  
  // Setup web server API endpoints
  setupWebServer();
  
  if (sdCardOK && microphoneOK && wifiConnected) {
    Serial.println("\nSystem ready! Access the web interface or use commands:");
    Serial.println("  'start' - Start recording");
    Serial.println("  'stop'  - Stop recording");
    Serial.println("  'upload' - Upload last recording to server");
    Serial.println("  'test'  - Run diagnostics again");
    Serial.println("----------------------------------------");
  } else {
    Serial.println("\nSystem NOT ready! Please fix hardware issues.");
    Serial.println("You can type 'test' to run diagnostics again.");
  }
}

void loop() {
  // Handle web server client requests
  server.handleClient();
  
  // Check for commands from Serial Monitor
  checkSerialCommands();
  
  // If recording, process audio data
  if (isRecording) {
    processAudioData();
  }
  
  // Small delay to prevent CPU hogging
  delay(10);
}

void setupWebServer() {
  // Define API endpoints
  server.on("/", HTTP_GET, handleRoot);
  server.on("/status", HTTP_GET, handleStatus);
  server.on("/start", HTTP_POST, handleStartRecording);
  server.on("/stop", HTTP_POST, handleStopRecording);
  server.on("/upload", HTTP_POST, handleUploadRecording);
  server.on("/test", HTTP_POST, handleRunDiagnostics);
  
  // Enable CORS
  server.enableCORS(true);
  
  // Start server
  server.begin();
  Serial.println("HTTP server started on port 80");
}

void handleRoot() {
  String html = "<html><body>";
  html += "<h1>ESP32 Audio Recorder</h1>";
  html += "<p>Use the API endpoints to control recording:</p>";
  html += "<ul>";
  html += "<li>GET /status - Device status</li>";
  html += "<li>POST /start - Start recording</li>";
  html += "<li>POST /stop - Stop recording</li>";
  html += "<li>POST /upload - Upload last recording</li>";
  html += "<li>POST /test - Run diagnostics</li>";
  html += "</ul>";
  html += "</body></html>";
  
  server.send(200, "text/html", html);
}

void handleStatus() {
  DynamicJsonDocument doc(1024);
  
  doc["isRecording"] = isRecording;
  doc["sdCardOK"] = sdCardOK;
  doc["microphoneOK"] = microphoneOK;
  doc["wifiConnected"] = wifiConnected;
  doc["currentFilename"] = currentFilename;
  
  if (isRecording) {
    doc["recordingTime"] = (millis() - recordingStartTime) / 1000;
  } else if (recordingDuration > 0) {
    doc["lastRecordingDuration"] = recordingDuration / 1000;
  }
  
  String response;
  serializeJson(doc, response);
  
  server.send(200, "application/json", response);
}

void handleStartRecording() {
  if (!sdCardOK || !microphoneOK) {
    server.send(400, "application/json", "{\"status\":\"error\",\"message\":\"Hardware issues detected. Run diagnostics first.\"}");
    return;
  }
  
  if (isRecording) {
    server.send(400, "application/json", "{\"status\":\"error\",\"message\":\"Already recording\"}");
    return;
  }
  
  startRecording();
  server.send(200, "application/json", "{\"status\":\"success\",\"message\":\"Recording started\",\"filename\":\"" + currentFilename + "\"}");
}

void handleStopRecording() {
  if (!isRecording) {
    server.send(400, "application/json", "{\"status\":\"error\",\"message\":\"Not currently recording\"}");
    return;
  }
  
  stopRecording();
  server.send(200, "application/json", "{\"status\":\"success\",\"message\":\"Recording stopped\",\"filename\":\"" + currentFilename + "\",\"duration\":" + String(recordingDuration / 1000) + "}");
}

void handleUploadRecording() {
  if (currentFilename.isEmpty()) {
    server.send(400, "application/json", "{\"status\":\"error\",\"message\":\"No recording available to upload\"}");
    return;
  }
  
  // Start upload in background
  server.send(200, "application/json", "{\"status\":\"success\",\"message\":\"Upload started\",\"filename\":\"" + currentFilename + "\"}");
  
  // Now perform the upload
  uploadRecording(currentFilename);
}

void handleRunDiagnostics() {
  if (isRecording) {
    server.send(400, "application/json", "{\"status\":\"error\",\"message\":\"Cannot run diagnostics while recording\"}");
    return;
  }
  
  // Run diagnostics
  runDiagnostics();
  setupWiFi();
  
  // Send response
  DynamicJsonDocument doc(1024);
  doc["status"] = "success";
  doc["sdCardOK"] = sdCardOK;
  doc["microphoneOK"] = microphoneOK;
  doc["wifiConnected"] = wifiConnected;
  
  String response;
  serializeJson(doc, response);
  
  server.send(200, "application/json", response);
}

void setupWiFi() {
  Serial.println("Testing WiFi connection...");
  
  WiFi.begin(ssid, password);
  
  // Wait for connection for up to 10 seconds
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi connected!");
    Serial.print("   IP address: ");
    Serial.println(WiFi.localIP());
    wifiConnected = true;
  } else {
    Serial.println("\n❌ Failed to connect to WiFi. Check credentials.");
    wifiConnected = false;
  }
}

void runDiagnostics() {
  Serial.println("\n----- Running Hardware Diagnostics -----");
  
  // Test SD card
  testSDCard();
  
  // Test microphone
  testMicrophone();
  
  // Report overall status
  Serial.println("\n----- Diagnostic Results -----");
  Serial.print("SD Card: ");
  if (sdCardOK) {
    Serial.println("GOOD ✓");
  } else {
    Serial.println("FAILED ✗");
  }
  
  Serial.print("Microphone: ");
  if (microphoneOK) {
    Serial.println("GOOD ✓");
  } else {
    Serial.println("FAILED ✗");
  }
  
  Serial.println("-------------------------------");
}

void testSDCard() {
  Serial.println("Testing SD card...");
  
  // Initialize SPI
  SPI.begin(SD_SCK, SD_MISO, SD_MOSI);
  
  // Try to initialize the SD card
  if (!SD.begin(SD_CS)) {
    Serial.println("❌ SD card initialization failed! Check connections.");
    sdCardOK = false;
    return;
  }
  
  // Check card type
  uint8_t cardType = SD.cardType();
  if (cardType == CARD_NONE) {
    Serial.println("❌ No SD card detected! Check if card is inserted.");
    sdCardOK = false;
    return;
  }
  
  String cardTypeStr = "UNKNOWN";
  if (cardType == CARD_MMC) cardTypeStr = "MMC";
  else if (cardType == CARD_SD) cardTypeStr = "SDSC";
  else if (cardType == CARD_SDHC) cardTypeStr = "SDHC";
  
  // Get card size
  uint64_t cardSize = SD.cardSize() / (1024 * 1024);
  
  // Check R/W by writing and reading a test file
  const char* testFileName = "/test.txt";
  const char* testData = "ESP32 SD Card Test";
  
  // Write test file
  File testFile = SD.open(testFileName, FILE_WRITE);
  if (!testFile) {
    Serial.println("❌ Failed to open test file for writing!");
    sdCardOK = false;
    return;
  }
  
  if (testFile.print(testData)) {
    // Write successful
  } else {
    Serial.println("❌ Failed to write to test file!");
    testFile.close();
    sdCardOK = false;
    return;
  }
  testFile.close();
  
  // Read test file
  testFile = SD.open(testFileName);
  if (!testFile) {
    Serial.println("❌ Failed to open test file for reading!");
    sdCardOK = false;
    return;
  }
  
  String readData = testFile.readString();
  testFile.close();
  
  if (readData != testData) {
    Serial.println("❌ Data verification failed!");
    sdCardOK = false;
    return;
  }
  
  // Clean up
  SD.remove(testFileName);
  
  Serial.println("✅ SD card working properly!");
  Serial.printf("   Card type: %s, Size: %lluMB\n", cardTypeStr.c_str(), cardSize);
  
  sdCardOK = true;
}

void testMicrophone() {
  Serial.println("Testing microphone...");
  
  // Initialize I2S
  i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = (i2s_bits_per_sample_t)SAMPLE_BITS,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = BUFFER_SIZE,
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };
  
  i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_SCK,
    .ws_io_num = I2S_WS,
    .data_out_num = I2S_PIN_NO_CHANGE,
    .data_in_num = I2S_SD
  };
  
  // Try to install the I2S driver
  esp_err_t result = i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
  if (result != ESP_OK) {
    Serial.println("❌ Failed to install I2S driver!");
    microphoneOK = false;
    return;
  }
  
  result = i2s_set_pin(I2S_PORT, &pin_config);
  if (result != ESP_OK) {
    Serial.println("❌ Failed to set I2S pins!");
    i2s_driver_uninstall(I2S_PORT);
    microphoneOK = false;
    return;
  }
  
  // Start collecting audio data
  uint8_t buffer[BUFFER_SIZE];
  size_t bytes_read;
  
  Serial.println("Please make some noise (speak, clap, tap mic)...");
  
  int16_t maxAmplitude = 0;
  int16_t minAmplitude = 0;
  unsigned long startTime = millis();
  
  // Collect audio samples for the test duration
  while (millis() - startTime < MIC_TEST_DURATION_MS) {
    // Read audio data from I2S
    i2s_read(I2S_PORT, buffer, sizeof(buffer), &bytes_read, 0);
    
    if (bytes_read > 0) {
      // Process the buffer as 16-bit samples to find amplitude
      int16_t* samples = (int16_t*)buffer;
      int samplesRead = bytes_read / 2; // Each sample is 2 bytes
      
      for (int i = 0; i < samplesRead; i++) {
        // Update max and min amplitude
        if (samples[i] > maxAmplitude) maxAmplitude = samples[i];
        if (samples[i] < minAmplitude) minAmplitude = samples[i];
      }
    }
    
    // Show progress dots
    static unsigned long lastDotTime = 0;
    if (millis() - lastDotTime >= 200) {
      Serial.print(".");
      lastDotTime = millis();
    }
  }
  
  // Clean up I2S
  i2s_driver_uninstall(I2S_PORT);
  
  // Calculate peak-to-peak amplitude
  int16_t peakToPeak = maxAmplitude - minAmplitude;
  
  Serial.println("");
  Serial.printf("   Peak-to-peak amplitude: %d\n", peakToPeak);
  
  if (peakToPeak > MIC_AMPLITUDE_THRESHOLD) {
    Serial.println("✅ Microphone detected audio input!");
    microphoneOK = true;
  } else {
    Serial.println("❌ Low or no audio detected. Check microphone connections.");
    microphoneOK = false;
  }
}

void checkSerialCommands() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command.equalsIgnoreCase("start")) {
      if (!sdCardOK || !microphoneOK) {
        Serial.println("Cannot start recording - hardware issues detected!");
        Serial.println("Run diagnostics with 'test' command first.");
      } else if (!isRecording) {
        startRecording();
      } else {
        Serial.println("Already recording!");
      }
    } 
    else if (command.equalsIgnoreCase("stop")) {
      if (isRecording) {
        stopRecording();
      } else {
        Serial.println("Not currently recording!");
      }
    }
    else if (command.equalsIgnoreCase("upload")) {
      if (!currentFilename.isEmpty()) {
        uploadRecording(currentFilename);
      } else {
        Serial.println("No recording available to upload!");
      }
    }
    else if (command.equalsIgnoreCase("test")) {
      if (isRecording) {
        Serial.println("Cannot run diagnostics while recording!");
        Serial.println("Stop recording first.");
      } else {
        runDiagnostics();
        // Also check WiFi connection
        setupWiFi();
      }
    }
    else {
      Serial.println("Unknown command. Use 'start', 'stop', 'upload', or 'test'");
    }
  }
}

void initI2S() {
  Serial.println("Initializing I2S...");
  
  i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = (i2s_bits_per_sample_t)SAMPLE_BITS,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = BUFFER_SIZE,
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };
  
  i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_SCK,
    .ws_io_num = I2S_WS,
    .data_out_num = I2S_PIN_NO_CHANGE,
    .data_in_num = I2S_SD
  };
  
  i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
  i2s_set_pin(I2S_PORT, &pin_config);
}

void startRecording() {
  // Initialize I2S for recording
  initI2S();
  
  // Create a new filename with a counter to avoid overwriting
  currentFilename = "/recording_" + String(fileCounter++) + ".wav";
  
  // Open file for writing
  audioFile = SD.open(currentFilename, FILE_WRITE);
  if (!audioFile) {
    Serial.println("Failed to open file for writing!");
    return;
  }
  
  // Write a placeholder header (will be updated when closing)
  wav_header_t header;
  // Set header fields to zero for now (will update when stopping)
  header.chunk_size = 0;
  header.data_size = 0;
  
  audioFile.write((const uint8_t*)&header, sizeof(wav_header_t));
  
  // Set recording flag and start time
  isRecording = true;
  recordingStartTime = millis();
  
  Serial.println("Recording started: " + currentFilename);
  Serial.println("Type 'stop' to end recording");
}

void stopRecording() {
  if (!isRecording || !audioFile) {
    return;
  }
  
  isRecording = false;
  
  // Get the size of recorded data (excluding header)
  uint32_t data_size = audioFile.size() - sizeof(wav_header_t);
  
  // Update the WAV header with the actual size
  wav_header_t header;
  header.chunk_size = data_size + 36; // 36 = size of the rest of the header
  header.data_size = data_size;
  
  // Seek back to the beginning of the file and write the updated header
  audioFile.seek(0);
  audioFile.write((const uint8_t*)&header, sizeof(wav_header_t));
  
  // Close the file
  audioFile.close();
  
  // Clean up I2S
  i2s_driver_uninstall(I2S_PORT);
  
  // Calculate and display recording duration
  recordingDuration = millis() - recordingStartTime;
  unsigned long duration = recordingDuration / 1000;
  Serial.println("Recording stopped!");
  Serial.printf("Duration: %lu seconds\n", duration);
  Serial.println("File size: " + String(data_size + sizeof(wav_header_t)) + " bytes");
  Serial.println("Ready for next command (start/stop/upload/test)");
}

void processAudioData() {
  // Buffer for audio data
  uint8_t buffer[BUFFER_SIZE];
  size_t bytes_read = 0;
  
  // Read audio data from I2S
  i2s_read(I2S_PORT, buffer, sizeof(buffer), &bytes_read, 0);
  
  if (bytes_read > 0) {
    // Write audio data to file
    audioFile.write(buffer, bytes_read);
    
    // Periodically display recording progress
    unsigned long elapsedSecs = (millis() - recordingStartTime) / 1000;
    static unsigned long lastReportTime = 0;
    
    if (millis() - lastReportTime >= 1000) {  // Update every second
      Serial.printf("Recording... %lu seconds\n", elapsedSecs);
      lastReportTime = millis();
    }
  }
}

void uploadRecording(String filename) {
  // Check WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected! Reconnecting...");
    setupWiFi();
    if (!wifiConnected) {
      Serial.println("Failed to reconnect to WiFi. Upload cancelled.");
      return;
    }
  }
  
  Serial.println("Opening file: " + filename);
  File file = SD.open(filename, FILE_READ);
  if (!file) {
    Serial.println("Failed to open file for reading!");
    return;
  }
  
  uint32_t fileSize = file.size();
  Serial.println("File size: " + String(fileSize) + " bytes");
  
  // Create HTTP client
  HTTPClient http;
  http.setConnectTimeout(10000); // 10 seconds timeout for connection
  
  Serial.print("Connecting to server...");
  // Start connection and send HTTP header
  http.begin(serverUrl);
  http.addHeader("Content-Type", "audio/wav");
  http.addHeader("Content-Disposition", "attachment; filename=" + filename.substring(1)); // Remove leading slash
  
  Serial.println("Uploading file...");
  
  // Start the POST request with the file size
  int httpCode = http.sendRequest("POST", &file, fileSize);
  
  // httpCode will be negative on error
  if (httpCode > 0) {
    Serial.printf("HTTP Response code: %d\n", httpCode);
    if (httpCode == HTTP_CODE_OK) {
      String payload = http.getString();
      Serial.println("Server response: " + payload);
    }
  } else {
    Serial.printf("HTTP POST failed, error: %s\n", http.errorToString(httpCode).c_str());
  }
  
  http.end();
  file.close();
  Serial.println("Upload process completed!");
}