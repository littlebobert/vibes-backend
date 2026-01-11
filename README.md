# Vibes Backend 📸✨

Backend for the Vibes iOS app - a workshop project where users take photos and get AI-generated "vibe scores" with funny explanations.

## Features

- 📤 **Photo Upload API** - Accept photos from iOS app with user name
- 🤖 **AI Vibe Scoring** - Uses Claude to analyze photos and generate scores (1-10) with witty roasts
- 🏆 **Live Leaderboard** - Web page showing all submissions ranked by score
- 🗑️ **Delete Submissions** - Users can remove their submissions if they're not happy

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure API Key

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your Anthropic API key
```

### 3. Run the Server

```bash
python main.py
```

The server will start at `http://localhost:8000`

### 4. Expose with ngrok (for iOS devices)

```bash
ngrok http 8000
```

Use the ngrok URL in your iOS app.

## API Endpoints

### Upload Photo
```
POST /api/upload
Content-Type: multipart/form-data

Fields:
- photo: Image file (JPEG, PNG, GIF, WebP, HEIC)
- name: User's name/nickname (string)

Response:
{
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "name": "Justin",
    "vibe_score": 7,
    "explanation": "Looks like they mass-assign their way through life and somehow it works",
    "photo_url": "/uploads/abc123.jpg"
}
```

### Get All Submissions
```
GET /api/submissions

Response: Array of submissions sorted by score (highest first)
```

### Delete Submission
```
DELETE /api/submissions/{id}

Response:
{
    "success": true,
    "message": "Submission deleted successfully"
}
```

### Health Check
```
GET /api/health

Response:
{
    "status": "healthy",
    "message": "Vibes backend is running! 🎉"
}
```

## Leaderboard

Visit `http://localhost:8000` (or your ngrok URL) in a browser to see the live leaderboard.

- Shows all submissions ranked by vibe score
- Auto-refreshes every 30 seconds
- Click photos to view full size
- Delete button appears on hover

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `MAX_SUBMISSIONS_PER_USER` | 3 | Max photos per person |
| `MAX_FILE_SIZE` | 10MB | Maximum upload size |

## iOS App Integration

Your iOS app should:

1. Capture a photo from camera or library
2. Collect user's name/nickname
3. POST to `/api/upload` as multipart form data
4. Display the returned vibe score and explanation

Example Swift code:

```swift
func uploadPhoto(image: UIImage, name: String) async throws -> VibeResult {
    let url = URL(string: "YOUR_NGROK_URL/api/upload")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    
    let boundary = UUID().uuidString
    request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
    
    var body = Data()
    
    // Add name field
    body.append("--\(boundary)\r\n".data(using: .utf8)!)
    body.append("Content-Disposition: form-data; name=\"name\"\r\n\r\n".data(using: .utf8)!)
    body.append("\(name)\r\n".data(using: .utf8)!)
    
    // Add photo
    body.append("--\(boundary)\r\n".data(using: .utf8)!)
    body.append("Content-Disposition: form-data; name=\"photo\"; filename=\"photo.jpg\"\r\n".data(using: .utf8)!)
    body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
    body.append(image.jpegData(compressionQuality: 0.8)!)
    body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
    
    request.httpBody = body
    
    let (data, _) = try await URLSession.shared.data(for: request)
    return try JSONDecoder().decode(VibeResult.self, from: data)
}
```

## Project Structure

```
vibes-backend/
├── main.py              # FastAPI application
├── database.py          # SQLite database operations
├── models.py            # Pydantic models
├── vibe_analyzer.py     # Anthropic API integration
├── requirements.txt     # Python dependencies
├── .env                 # API keys (create from .env.example)
├── templates/
│   └── leaderboard.html # Leaderboard web page
├── static/              # Static assets
└── uploads/             # Uploaded photos
```

## License

MIT - Have fun! 🎉

