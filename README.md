# kleinsniffer 🔎

A command-line tool to scrape and monitor listings from Kleinanzeigen (formerly eBay Kleinanzeigen), a popular German online classifieds marketplace

## Features ✨

*   **Search and Filter:** Scrape listings based on a user-defined search query and price range. 🔍
*   **Regular Updates:** Monitor listings at a specified interval and notify you of new results. ⏰
*   **History:** Keep track of previously found listings. 📜
*   **User-Friendly Interface:** Simple command-line interface with colorful output using Rich. 🎨
*   **Configurable:** Set search parameters, update interval, and history size via interactive prompts. ⚙️

## Requirements 💻

*   Python 3.6+
*   pip

## Installation 🛠️

1.  Clone the repository:

    ```bash
    git clone https://github.com/br0sinski/kleinsniffer.git
    cd kleinsniffer
    ```

2.  Create a virtual environment (recommended):

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  Install the dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Usage 🚀

Run the script:

```bash
python main.py
```

## Configuration ⚙️

The script will guide you through an interactive configuration process. You'll be asked to provide:

*   **Search Query:** The item you're looking for (e.g., "nintendo switch").
*   **Minimum Price:** The lower bound of the price range.
*   **Maximum Price:** The upper bound of the price range.
*   **Update Interval:** How often (in minutes) the script should check for new listings.
*   **History Size:** The number of past listings to store in the history.
*   **Initial Ads:** The number of ads to display initially.

## Contributing 🤝

Feel free to contribute to the project by submitting pull requests, reporting issues, or suggesting new features.

## License 📄

This project is licensed under the MIT License.
