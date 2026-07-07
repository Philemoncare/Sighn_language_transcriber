import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  static const primaryColor = Color(0xFFF97316); // Orange
  static const secondaryColor = Color(0xFFFBBF24); // Amber
  static const backgroundColor = Color(0xFFFAFAFA);
  static const cardColor = Color(0xFFFFFFFF);
  static const darkColor = Color(0xFF171717);

  static const darkBackgroundColor = Color(0xFF09090B);
  static const darkSurfaceColor = Color(0xFF0C0C0D);
  static const darkSurfaceRaisedColor = Color(0xFF121214);
  static const darkBorderColor = Color(0x0FFFFFFF);

  static final darkTheme = ThemeData(
    brightness: Brightness.dark,
    scaffoldBackgroundColor: darkBackgroundColor,
    primaryColor: primaryColor,
    colorScheme: const ColorScheme.dark(
      primary: primaryColor,
      secondary: secondaryColor,
      surface: darkSurfaceColor,
      background: darkBackgroundColor,
      onPrimary: Colors.white,
    ),
    textTheme: GoogleFonts.plusJakartaSansTextTheme(
      ThemeData.dark().textTheme,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: darkBackgroundColor,
      foregroundColor: Colors.white,
      elevation: 0,
      centerTitle: false,
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: primaryColor,
        foregroundColor: Colors.white,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: darkSurfaceRaisedColor,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: darkBorderColor),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: darkBorderColor),
      ),
    ),
    cardTheme: CardTheme(
      color: darkSurfaceRaisedColor,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: darkBorderColor),
      ),
      elevation: 0,
    ),
  );
}
