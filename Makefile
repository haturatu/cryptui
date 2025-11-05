.PHONY: all build install uninstall clean

CONFIG_DIR = /usr/local/etc/cryptui

all: build

build:
	python3 -m build

install:
	pip install . --force-reinstall
	@echo "Installing configuration files to $(CONFIG_DIR)..."
	@sudo mkdir -p $(CONFIG_DIR)
	@sudo cp config.ini.example $(CONFIG_DIR)/config.ini
	@sudo cp notification.md.example $(CONFIG_DIR)/notification.md
	@echo "Done! Run 'cryptui -h' to get started."

uninstall:
	pip uninstall cryptui -y
	@echo "Removing configuration files from $(CONFIG_DIR)..."
	@sudo rm -rf $(CONFIG_DIR)

clean:
	rm -rf build dist *.egg-info
