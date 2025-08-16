#include <iostream>
#include <string>
#include <vector>
#include <sndfile.h>
#include <keyfinder/keyfinder.h>

class KeyFinderCLI {
private:
    KeyFinder::KeyFinder keyFinder;
    
    // Convert libKeyFinder key to string
    std::string keyToString(KeyFinder::key_t key) {
        switch(key) {
            case KeyFinder::A_MAJOR: return "A";
            case KeyFinder::A_MINOR: return "Am";
            case KeyFinder::B_FLAT_MAJOR: return "A#";
            case KeyFinder::B_FLAT_MINOR: return "A#m";
            case KeyFinder::B_MAJOR: return "B";
            case KeyFinder::B_MINOR: return "Bm";
            case KeyFinder::C_MAJOR: return "C";
            case KeyFinder::C_MINOR: return "Cm";
            case KeyFinder::D_FLAT_MAJOR: return "C#";
            case KeyFinder::D_FLAT_MINOR: return "C#m";
            case KeyFinder::D_MAJOR: return "D";
            case KeyFinder::D_MINOR: return "Dm";
            case KeyFinder::E_FLAT_MAJOR: return "D#";
            case KeyFinder::E_FLAT_MINOR: return "D#m";
            case KeyFinder::E_MAJOR: return "E";
            case KeyFinder::E_MINOR: return "Em";
            case KeyFinder::F_MAJOR: return "F";
            case KeyFinder::F_MINOR: return "Fm";
            case KeyFinder::G_FLAT_MAJOR: return "F#";
            case KeyFinder::G_FLAT_MINOR: return "F#m";
            case KeyFinder::G_MAJOR: return "G";
            case KeyFinder::G_MINOR: return "Gm";
            case KeyFinder::A_FLAT_MAJOR: return "G#";
            case KeyFinder::A_FLAT_MINOR: return "G#m";
            default: return "Unknown";
        }
    }
    
    // Convert to Camelot notation for DJ mixing
    std::string toCamelot(const std::string& key) {
        if (key == "C") return "8B";
        if (key == "Am") return "8A";
        if (key == "G") return "9B";
        if (key == "Em") return "9A";
        if (key == "D") return "10B";
        if (key == "Bm") return "10A";
        if (key == "A") return "11B";
        if (key == "F#m") return "11A";
        if (key == "E") return "12B";
        if (key == "C#m") return "12A";
        if (key == "B") return "1B";
        if (key == "G#m") return "1A";
        if (key == "F#") return "2B";
        if (key == "D#m") return "2A";
        if (key == "C#") return "3B";
        if (key == "A#m") return "3A";
        if (key == "G#") return "4B";
        if (key == "Fm") return "4A";
        if (key == "D#") return "5B";
        if (key == "Cm") return "5A";
        if (key == "A#") return "6B";
        if (key == "Gm") return "6A";
        if (key == "F") return "7B";
        if (key == "Dm") return "7A";
        return "Unknown";
    }
    
public:
    std::string detectKey(const std::string& audioFile) {
        try {
            // Open audio file using libsndfile
            SF_INFO sfInfo;
            SNDFILE* file = sf_open(audioFile.c_str(), SFM_READ, &sfInfo);
            
            if (!file) {
                return "Error: Could not open audio file";
            }
            
            // Read audio data
            std::vector<float> audioData(sfInfo.frames * sfInfo.channels);
            sf_count_t framesRead = sf_readf_float(file, audioData.data(), sfInfo.frames);
            sf_close(file);
            
            if (framesRead == 0) {
                return "Error: Could not read audio data";
            }
            
            // Prepare AudioData for KeyFinder
            KeyFinder::AudioData audio;
            audio.setFrameRate(sfInfo.samplerate);
            audio.setChannels(sfInfo.channels);
            audio.addToSampleCount(framesRead * sfInfo.channels);
            
            // Copy audio data
            for (int i = 0; i < framesRead * sfInfo.channels; i++) {
                audio.setSample(i, audioData[i]);
            }
            
            // Detect key
            KeyFinder::key_t key = keyFinder.keyOfAudio(audio);
            std::string keyString = keyToString(key);
            std::string camelot = toCamelot(keyString);
            
            return keyString + " (" + camelot + ")";
            
        } catch (const std::exception& e) {
            return "Error: " + std::string(e.what());
        }
    }
};

int main(int argc, char* argv[]) {
    if (argc != 2) {
        std::cout << "Usage: keyfinder_cli <audio_file>" << std::endl;
        return 1;
    }
    
    std::string audioFile = argv[1];
    KeyFinderCLI cli;
    std::string result = cli.detectKey(audioFile);
    
    std::cout << result << std::endl;
    return 0;
} 