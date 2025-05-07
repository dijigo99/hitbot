# HitBot - Google Referrer Test Bot

A Python tool that generates realistic traffic to your website with Google referrals and Gmail cookie support using proxies.

## Features

- Simulates Google search behavior before visiting your site
- Uses proxies with HTTP/SOCKS support for anonymity
- Rotates user agents to appear as different browsers
- Includes cookie support for authenticated sessions
- Configurable request count and timeout
- Direct connection mode for testing without proxies
- Keyword-based Google searches with target site clicks

## Setup

1. Install required dependencies:
   ```
   pip install requests python-dotenv beautifulsoup4
   ```

2. Configure your settings in `.env` file:
   ```
   TARGET_URL=https://your-website.com
   REQUEST_COUNT=25
   TIMEOUT=10
   USE_DIRECT_CONNECTION=false  # Set to true to bypass proxy usage
   ```

3. Add your proxies to `proxies.txt` (one per line):
   ```
   http://username:password@proxy1:port
   socks5://username:password@proxy2:port
   http://proxy3:port
   ```

4. Add your browser user agents to `user_agents.txt` (one per line)

5. Add your search keywords to `keywords.txt` (one per line):
   ```
   web tasarım
   dijital pazarlama
   web geliştirme
   ```

6. Export your Google/Gmail cookies to `cookies.json` (you can use browser extensions like "Cookie-Editor" to export cookies)

## Usage

Run the script with:

```
python hitbot.py
```

The script will:
1. Choose a random keyword from keywords.txt
2. Search for that keyword + your website domain on Google
3. Find and click your website in the search results
4. Rotate through different proxies and user agents

### Testing Without Proxies

If you want to test the script without using proxies, set `USE_DIRECT_CONNECTION=true` in your `.env` file. This will make direct connections to the target website and Google without routing through a proxy.

## Cookie Export Guide

To export cookies from your browser:
1. Install a cookie manager extension (like "Cookie-Editor" for Chrome/Firefox)
2. Navigate to Google.com
3. Open the extension
4. Export cookies as JSON
5. Save to `cookies.json` in the project directory

## Customization

- Modify the search behavior in the `simulate_google_search` function
- Adjust request delays in the main loop to simulate more human-like behavior
- Add additional HTTP headers in the `create_session` function
- Edit keywords.txt to target specific search terms relevant to your website

## Disclaimer

This tool is for testing purposes only. Please ensure you comply with the terms of service of any website you test with this tool. 

## Deployment to Render.com

To deploy this application to render.com:

1. Fork or push this repository to GitHub or GitLab

2. On render.com, create a new Web Service and connect to your repository

3. Use the following settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python app.py`

4. Add the following environment variables:
   - `PORT`: 10000 (or any port render.com assigns)
   - `TARGET_URL`: Your target website URL
   - `REQUEST_COUNT`: Number of requests to make
   - `TIMEOUT`: Request timeout in seconds
   - `USE_DIRECT_CONNECTION`: "true" or "false"
   - Other settings as needed

5. Deploy the service

The application comes with a `render.yaml` file which can be used for automatic configuration when deploying to render.com. 