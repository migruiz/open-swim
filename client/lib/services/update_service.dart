import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:package_info_plus/package_info_plus.dart';
import 'package:path_provider/path_provider.dart';
import 'package:open_filex/open_filex.dart';

/// Configuration for GitHub repository
const String githubOwner = 'YOUR_GITHUB_USERNAME'; // TODO: Replace with your GitHub username
const String githubRepo = 'open-swim'; // TODO: Replace with your repo name if different

class UpdateInfo {
  final String version;
  final String downloadUrl;
  final String releaseNotes;

  UpdateInfo({
    required this.version,
    required this.downloadUrl,
    required this.releaseNotes,
  });
}

class UpdateService {
  static final UpdateService _instance = UpdateService._internal();
  factory UpdateService() => _instance;
  UpdateService._internal();

  /// Check if a new version is available on GitHub Releases
  Future<UpdateInfo?> checkForUpdate() async {
    try {
      final response = await http.get(
        Uri.parse(
            'https://api.github.com/repos/$githubOwner/$githubRepo/releases/latest'),
        headers: {'Accept': 'application/vnd.github.v3+json'},
      );

      if (response.statusCode != 200) {
        return null;
      }

      final data = json.decode(response.body);
      final tagName = data['tag_name'] as String;
      final latestVersion = tagName.replaceFirst('v', '');

      final packageInfo = await PackageInfo.fromPlatform();
      final currentVersion = packageInfo.version;

      if (_isNewerVersion(latestVersion, currentVersion)) {
        // Find APK asset
        final assets = data['assets'] as List;
        final apkAsset = assets.firstWhere(
          (asset) => (asset['name'] as String).endsWith('.apk'),
          orElse: () => null,
        );

        if (apkAsset == null) {
          return null;
        }

        return UpdateInfo(
          version: latestVersion,
          downloadUrl: apkAsset['browser_download_url'] as String,
          releaseNotes: data['body'] as String? ?? '',
        );
      }

      return null;
    } catch (e) {
      print('Error checking for updates: $e');
      return null;
    }
  }

  /// Compare version strings (e.g., "1.2.3" > "1.2.0")
  bool _isNewerVersion(String latest, String current) {
    final latestParts = latest.split('.').map(int.parse).toList();
    final currentParts = current.split('.').map(int.parse).toList();

    for (int i = 0; i < latestParts.length && i < currentParts.length; i++) {
      if (latestParts[i] > currentParts[i]) return true;
      if (latestParts[i] < currentParts[i]) return false;
    }

    return latestParts.length > currentParts.length;
  }

  /// Download and install the APK
  Future<bool> downloadAndInstall(
    String downloadUrl, {
    void Function(double progress)? onProgress,
  }) async {
    try {
      final client = http.Client();
      final request = http.Request('GET', Uri.parse(downloadUrl));
      final response = await client.send(request);

      final contentLength = response.contentLength ?? 0;
      final bytes = <int>[];
      int downloadedBytes = 0;

      await for (final chunk in response.stream) {
        bytes.addAll(chunk);
        downloadedBytes += chunk.length;
        if (contentLength > 0 && onProgress != null) {
          onProgress(downloadedBytes / contentLength);
        }
      }

      // Save to downloads directory
      final dir = await getExternalStorageDirectory();
      if (dir == null) {
        return false;
      }

      final file = File('${dir.path}/open-swim-update.apk');
      await file.writeAsBytes(bytes);

      // Open the APK for installation
      final result = await OpenFilex.open(file.path);
      return result.type == ResultType.done;
    } catch (e) {
      print('Error downloading update: $e');
      return false;
    }
  }
}
