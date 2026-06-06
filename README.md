# ByteTorrent

ByteTorrent is a command-line P2P application developed to let users share files over the same local network. The application splits files into chunks, announces those chunks to other users on the network, and downloads requested files by reassembling the chunks.

## Requirements

- Python 3.10 or newer
- At least two devices on the same local network
- Access to UDP `6000` and TCP `6001`
- `pip`

## Cloning the project

Clone the repository and enter the project directory:

```bash
git clone https://github.com/batuhankiskac/ByteTorrent.git
cd ByteTorrent
```
## Installation

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

## Running the application

```bash
python3 ByteTorrent.py
```

When the program starts, it launches the following background services:

- Discovery service over UDP `6000`
- Chunk transfer service over TCP `6001`

If startup succeeds, the main menu will appear.

## Main menu

The application provides these options:

1. `View users`
2. `View available content`
3. `Download content`
4. `View history`
5. `Host a file`
6. `Exit`

### 1. View users

Lists discovered users and their IP addresses on the network.

### 2. View available content

Lists file names announced on the network. The application derives these names from chunk names. For example, if the chunks are `forest_1`, `forest_2`, and `forest_3`, the visible content name will be `forest`.

### 3. Download content

To download a file, enter its name:

```text
Enter file name to download (e.g. forest): forest
Secure download? (y/n): y
```

Notes:

- Enter the base file name without the extension. Example: `forest`
- The application looks for `forest_1`, `forest_2`, and `forest_3` by default
- If all chunks are downloaded successfully, the file is merged automatically
- The merged file is written to the project root directory
- The output file uses the base name you entered. For example, if you download `forest`, the output file will also be named `forest`

### 4. View history

Reads the following log files:

- `download_history.log`
- `upload_history.log`

These files store timestamped records showing which chunk was received from whom and which chunk was sent to whom.

### 5. Host a file

To host a file:

1. Enter the file path or file name
2. Enter your username

Example:

```text
Enter file name to host: sample.pdf
Enter your username: batuhan
```

After that, the application:

- Splits the file into 3 chunks
- Saves the chunks into the `chunks/` folder
- Starts announcing those chunks to the network at regular intervals

Once hosting has started, if you add another file, the application also adds that file's chunks to the current hosted set.

### 6. Exit

Safely closes the program and stops the background services.

## Generated files and folders

While running, the program may create these files and folders in the project directory:

- `chunks/`: file chunks that are shared or downloaded
- `network_state.json`: discovered users and chunks on the network
- `download_history.log`: download history
- `upload_history.log`: upload history

## Network and port information

Default settings:

- UDP discovery port: `6000`
- TCP chunk transfer port: `6001`
- Announcement interval: `8` seconds
- Discovery cleanup interval: `60` seconds
- Default chunk count: `3`

The broadcast address can be changed with an environment variable:

```bash
BT_BROADCAST_IP=192.168.1.255 python3 ByteTorrent.py
```
