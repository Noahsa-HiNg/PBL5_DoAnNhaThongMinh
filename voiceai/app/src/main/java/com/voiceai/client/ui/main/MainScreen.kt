package com.voiceai.client.ui.main

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.voiceai.client.ui.alarms.SchedulesScreen
import com.voiceai.client.ui.alarms.SchedulesViewModel
import com.voiceai.client.ui.chat.ChatScreen
import com.voiceai.client.ui.chat.ChatViewModel
import com.voiceai.client.ui.devices.DevicesScreen
import com.voiceai.client.ui.devices.DevicesViewModel
import com.voiceai.client.ui.settings.SettingsScreen
import com.voiceai.client.ui.settings.SettingsViewModel
import org.koin.androidx.compose.koinViewModel

sealed class NavTab(
    val route: String,
    val label: String,
    val selectedIcon: ImageVector,
    val unselectedIcon: ImageVector
) {
    object Chat     : NavTab("chat",     "Chat",     Icons.Filled.Chat,     Icons.Outlined.Chat)
    object Devices  : NavTab("devices",  "Thiết bị", Icons.Filled.Devices,  Icons.Outlined.Devices)
    object Dashboard : NavTab("dashboard", "Cảm biến", Icons.Filled.BarChart, Icons.Outlined.BarChart)
    object Alarms   : NavTab("alarms",   "Hẹn giờ", Icons.Filled.Alarm,    Icons.Outlined.Alarm)
    object Settings : NavTab("settings", "Cài đặt",  Icons.Filled.Settings, Icons.Outlined.Settings)
}

private val navTabs = listOf(NavTab.Chat, NavTab.Devices, NavTab.Dashboard, NavTab.Alarms, NavTab.Settings)

@Composable
fun MainScreen() {
    val navController = rememberNavController()

    // ViewModels tạo ở đây để giữ state khi chuyển tab
    val chatViewModel: ChatViewModel         = koinViewModel()
    val devicesViewModel: DevicesViewModel   = koinViewModel()
    val dashboardViewModel: com.voiceai.client.ui.dashboard.SensorDashboardViewModel = koinViewModel()
    val schedulesViewModel: SchedulesViewModel = koinViewModel()
    val settingsViewModel: SettingsViewModel = koinViewModel()

    Scaffold(
        bottomBar = {
            NavigationBar {
                val navBackStackEntry by navController.currentBackStackEntryAsState()
                val currentDestination = navBackStackEntry?.destination

                navTabs.forEach { tab ->
                    val selected = currentDestination?.hierarchy?.any { it.route == tab.route } == true
                    NavigationBarItem(
                        selected = selected,
                        onClick = {
                            navController.navigate(tab.route) {
                                popUpTo(navController.graph.findStartDestination().id) {
                                    saveState = true
                                }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = {
                            Icon(
                                if (selected) tab.selectedIcon else tab.unselectedIcon,
                                contentDescription = tab.label
                            )
                        },
                        label = { Text(tab.label) }
                    )
                }
            }
        }
    ) { innerPadding ->
        // ⚠️ Fix: import Modifier + padding() extension riêng biệt
        // Không dùng fully-qualified androidx.compose.ui.Modifier.padding(...)
        NavHost(
            navController = navController,
            startDestination = NavTab.Chat.route,
            modifier = Modifier.padding(innerPadding)
        ) {
            composable(NavTab.Chat.route) {
                ChatScreen(viewModel = chatViewModel)
            }
            composable(NavTab.Devices.route) {
                DevicesScreen(viewModel = devicesViewModel)
            }
            composable(NavTab.Dashboard.route) {
                com.voiceai.client.ui.dashboard.SensorDashboardScreen(viewModel = dashboardViewModel)
            }
            composable(NavTab.Alarms.route) {
                SchedulesScreen(viewModel = schedulesViewModel)
            }
            composable(NavTab.Settings.route) {
                SettingsScreen(viewModel = settingsViewModel)
            }
        }
    }
}