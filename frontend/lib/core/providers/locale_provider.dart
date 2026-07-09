import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

const supportedLocales = [
  Locale('en'),
  Locale('am'),
  Locale('om'),
  Locale('ti'),
  Locale('so'),
];

const localeNames = {
  'en': 'English',
  'am': 'አማርኛ',
  'om': 'Afaan Oromoo',
  'ti': 'ትግርኛ',
  'so': 'Soomaali',
};

class LocaleController extends Notifier<Locale> {
  @override
  Locale build() => const Locale('en');

  void setLocale(Locale locale) => state = locale;
}

final localeControllerProvider = NotifierProvider<LocaleController, Locale>(LocaleController.new);

class ThemeModeController extends Notifier<ThemeMode> {
  @override
  ThemeMode build() => ThemeMode.system;

  void setThemeMode(ThemeMode mode) => state = mode;
}

final themeModeControllerProvider = NotifierProvider<ThemeModeController, ThemeMode>(
  ThemeModeController.new,
);
