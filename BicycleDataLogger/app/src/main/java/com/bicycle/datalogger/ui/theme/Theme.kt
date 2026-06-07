package com.bicycle.datalogger.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = Color(0xFF1976D2),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFBBDEFB),
    secondary = Color(0xFF43A047),
    onSecondary = Color.White,
    surface = Color(0xFFFAFAFA),
    onSurface = Color(0xFF212121),
    background = Color(0xFFF5F5F5),
    onBackground = Color(0xFF212121),
    error = Color(0xFFD32F2F),
)

@Composable
fun BicycleTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = LightColors,
        content = content
    )
}
