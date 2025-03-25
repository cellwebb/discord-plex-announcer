<!-- markdownlint-disable MD024 -->

# Changelog

All notable changes to the Discord Plex Announcer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Support for sending different types of announcements to different Discord channels:
  - `MOVIE_CHANNEL_ID`: Channel for movie announcements
  - `NEW_SHOWS_CHANNEL_ID`: Channel for new TV show announcements
  - `RECENT_EPISODES_CHANNEL_ID`: Channel for recent episode announcements
- If specialized channels are not specified, announcements will be sent to the default channel

### Fixed

- Added timeout parameter to Plex server connection to prevent the bot from hanging indefinitely
- Improved error handling for Plex API calls to gracefully handle connection timeouts
- Fixed logger definition in signal handler to properly handle termination signals

## [0.2.0] - 2025-03-22

### Added

- Split TV notifications into separate flags:
  - `NOTIFY_NEW_SHOWS`: Controls notifications for new TV shows (first episode of first season)
  - `NOTIFY_RECENT_EPISODES`: Controls notifications for recently aired episodes
- Added configurable timeframe for recent episodes with `RECENT_EPISODE_DAYS` (default: 30 days)
- Enhanced logging for better debugging and monitoring
- Automatic creation of data and logs directories

### Changed

- Updated Docker configuration to use the new environment variables
- Improved error handling for Plex API connections
- Enhanced Discord embeds to visually indicate when a show is new

### Fixed

- Fixed directory structure for data and logs
- Improved handling of air dates for TV episodes

## [0.1.0] - Initial Release

### Features

- Initial release of Discord Plex Announcer
- Support for monitoring Plex libraries for new movies and TV shows
- Discord notifications with rich embeds
- Admin commands for status, health checks, and manual refresh
- Docker support with healthcheck integration
