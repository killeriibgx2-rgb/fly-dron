package com.zzynes.flydrone.DRONE;

import com.zzynes.flydrone.DRONE.entity.FpvDroneEntity;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderHandEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

@Mod.EventBusSubscriber(modid = FlyDroneMod.MOD_ID, value = Dist.CLIENT)
public class FpvOverlay {

    public static final ResourceLocation OVERLAY = new ResourceLocation("fly_drone", "textures/gui/overlay_fpv.png");
    public static final ResourceLocation CONNECTION_LOST = new ResourceLocation("fly_drone", "textures/gui/connection_lost.png");

    public static boolean fpvActive = false;
    public static int connectionLostTimer = 0;
    public static float distance = 0;
    public static FpvDroneEntity drone = null;

    @SubscribeEvent
    public static void onRenderHand(RenderHandEvent event) {
        if (fpvActive) event.setCanceled(true);
    }

    public static void render(GuiGraphics g) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null || mc.level == null) return;

        if (connectionLostTimer > 0) {
            g.blit(CONNECTION_LOST, 0, 0, g.guiWidth(), g.guiHeight(), 0, 0, 512, 512, 512, 512);
            return;
        }

        if (!fpvActive || drone == null) return;

        int size = g.guiHeight();
        int x = (g.guiWidth() - size) / 2;
        float s = size / 512f;

        g.blit(OVERLAY, x, 0, size, size, 0, 0, 512, 512, 512, 512);

        int pct = Math.max(0, drone.getBatteryTicks() * 100 / 4800);
        g.drawString(mc.font, pct + "%", x + 206 * s, 242 * s, 0xFFFFFF, true);

        g.drawString(mc.font, "ДВИГ: " + (int) drone.getMotorTemp() + "°", 8, g.guiHeight() / 2 - 20, 0xFFFFFF, true);
        g.drawString(mc.font, "АКБ: " + (int) drone.getBatteryTemp() + "°", 8, g.guiHeight() / 2 - 8, 0xFFFFFF, true);

        boolean overheat = drone.getMotorTemp() >= 100 || drone.getBatteryTemp() >= 100;
        boolean low = pct <= 15;

        if (overheat && low) {
            String warn = (mc.level.getGameTime() / 10) % 2 == 0 ? "ПЕРЕГРЕВ" : "ПЕРЕРАЗРЯД";
            int w = mc.font.width(warn);
            g.drawString(mc.font, warn, (g.guiWidth() - w) / 2, 24, 0xFF2020, true);
        } else if (overheat && (mc.level.getGameTime() / 10) % 2 == 0) {
            int w = mc.font.width("ПЕРЕГРЕВ");
            g.drawString(mc.font, "ПЕРЕГРЕВ", (g.guiWidth() - w) / 2, 24, 0xFF2020, true);
        } else if (low && (mc.level.getGameTime() / 10) % 2 == 0) {
            int w = mc.font.width("ПЕРЕРАЗРЯД");
            g.drawString(mc.font, "ПЕРЕРАЗРЯД", (g.guiWidth() - w) / 2, 24, 0xFF2020, true);
        }

        if (distance >= 1800) {
            g.drawString(mc.font, "ДО ПОТЕРИ СИГНАЛА: " + (int) (2000 - distance) + " м", 8, g.guiHeight() / 2, 0xFFFF55, true);
        }
    }
}