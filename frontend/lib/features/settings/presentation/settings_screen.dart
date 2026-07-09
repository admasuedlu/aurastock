import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers/locale_provider.dart';
import '../../../l10n/generated/app_localizations.dart';
import '../../auth/providers/auth_controller.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final user = ref.watch(authControllerProvider).valueOrNull;
    final locale = ref.watch(localeControllerProvider);
    final themeMode = ref.watch(themeModeControllerProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.settings)),
      body: ListView(
        children: [
          if (user != null)
            ListTile(
              leading: const CircleAvatar(child: Icon(Icons.person)),
              title: Text(user.fullName.isEmpty ? user.email : user.fullName),
              subtitle: Text('${user.email} · ${user.roleName}'),
            ),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.language),
            title: Text(l10n.language),
            trailing: DropdownButton<Locale>(
              value: locale,
              underline: const SizedBox.shrink(),
              items: supportedLocales
                  .map((l) => DropdownMenuItem(value: l, child: Text(localeNames[l.languageCode]!)))
                  .toList(),
              onChanged: (value) {
                if (value != null) ref.read(localeControllerProvider.notifier).setLocale(value);
              },
            ),
          ),
          ListTile(
            leading: const Icon(Icons.dark_mode_outlined),
            title: const Text('Theme'),
            trailing: SegmentedButton<ThemeMode>(
              segments: const [
                ButtonSegment(value: ThemeMode.light, icon: Icon(Icons.light_mode_outlined)),
                ButtonSegment(value: ThemeMode.system, icon: Icon(Icons.brightness_auto_outlined)),
                ButtonSegment(value: ThemeMode.dark, icon: Icon(Icons.dark_mode_outlined)),
              ],
              selected: {themeMode},
              onSelectionChanged: (selection) =>
                  ref.read(themeModeControllerProvider.notifier).setThemeMode(selection.first),
            ),
          ),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.logout, color: Colors.red),
            title: Text(l10n.logout, style: const TextStyle(color: Colors.red)),
            onTap: () => ref.read(authControllerProvider.notifier).logout(),
          ),
        ],
      ),
    );
  }
}
