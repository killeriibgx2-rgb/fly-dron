package com.zzynes.flydrone.DRONE;

import com.zzynes.flydrone.DRONE.entity.FpvDroneEntity;
import com.zzynes.flydrone.DRONE.init.ModItems;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.HitResult;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.InputEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.lwjgl.glfw.GLFW;

import java.util.UUID;

@Mod.EventBusSubscriber(modid = FlyDroneMod.MOD_ID, value = Dist.CLIENT)
public class DroneInputHandler {

    private static float throttle = 0f;
    private static double lastMouseX = 0;
    private static double lastMouseY = 0;
    private static boolean mouseInit = false;
    private static UUID lastUuid = null;
    private static int lastViewRadius = 0;

    @SubscribeEvent
    public static void onMouse(InputEvent.MouseButton.Pre event) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null || mc.screen != null) return;

        if (event.getButton() == 1) {
            if (FpvOverlay.fpvActive) {
                event.setCanceled(true);
                return;
            }

            boolean aimingEntity = mc.hitResult != null && mc.hitResult.getType() == HitResult.Type.ENTITY;
            boolean remoteInMainHand = getMainHandConnectedRemote(mc.player) != null;

            if (remoteInMainHand && !aimingEntity) {
                FpvOverlay.fpvActive = true;
                mouseInit = false;
                resetMouseKeys(mc);
                event.setCanceled(true);
            }
        }
    }

    @SubscribeEvent
    public static void onKey(InputEvent.Key event) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null) return;
        if (FpvOverlay.fpvActive && event.getKey() == GLFW.GLFW_KEY_ESCAPE && event.getAction() == 1) {
            exitFpv(mc);
            event.setCanceled(true);
        }
    }

    @SubscribeEvent
    public static void onClientTick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getInstance();
        LocalPlayer player = mc.player;
        if (player == null || mc.level == null) {
            FpvOverlay.fpvActive = false;
            FpvOverlay.drone = null;
            return;
        }

        if (FpvOverlay.connectionLostTimer > 0) FpvOverlay.connectionLostTimer--;

        ItemStack stack = getConnectedRemote(player);
        if (stack == null) {
            exitFpv(mc);
            FpvOverlay.drone = null;
            return;
        }

        UUID uuid = stack.getTag().getUUID("DroneUUID");
        lastUuid = uuid;
        FpvDroneEntity drone = findDrone(mc, uuid);
        if (drone == null) {
            if (FpvOverlay.fpvActive) FpvOverlay.connectionLostTimer = 100;
            exitFpv(mc);
            FpvOverlay.drone = null;
            return;
        }

        double dist = player.distanceTo(drone);
        FpvOverlay.distance = (float) dist;
        FpvOverlay.drone = drone;

        if (FpvOverlay.fpvActive) {
            if (mc.getCameraEntity() != drone) mc.setCameraEntity(drone);

            int rd = mc.options.renderDistance().get();
            int needed = (int) (dist / 16) + rd + 4;
            if (needed != lastViewRadius) {
                lastViewRadius = needed;
                mc.level.getChunkSource().updateViewRadius(needed);
            }

            if (mc.options.keyUp.isDown()) {
                throttle = Math.min(1f, throttle + 0.25f);
            } else if (mc.options.keyDown.isDown()) {
                throttle = Math.max(0f, throttle - 0.06f);
            } else {
                throttle *= 0.6f;
                if (throttle < 0.01f) throttle = 0f;
            }

            player.setYRot(drone.getYRot());
            player.setXRot(drone.getXRot());

            double dx = 0, dy = 0;
            if (mouseInit) {
                dx = mc.mouseHandler.xpos() - lastMouseX;
                dy = mc.mouseHandler.ypos() - lastMouseY;
            }
            mouseInit = true;
            lastMouseX = mc.mouseHandler.xpos();
            lastMouseY = mc.mouseHandler.ypos();

            float pitchIn = (float) (dy * 0.8);
            float rollIn = (float) (dx * 0.8);

            float yawIn = 0f;
            if (mc.options.keyLeft.isDown()) yawIn += 2.0f;
            if (mc.options.keyRight.isDown()) yawIn -= 2.0f;

            ModNetwork.CHANNEL.sendToServer(new DroneControlPacket(
                    uuid, throttle, pitchIn, rollIn, yawIn, mc.options.renderDistance().get()
            ));
        } else {
            if (mc.getCameraEntity() != player) {
                mc.tell(() -> {
                    if (mc.player != null) mc.setCameraEntity(mc.player);
                });
            }
            mouseInit = false;
            throttle = 0f;
        }
    }

    public static void forceDisconnectClient(UUID droneUUID) {
        Minecraft mc = Minecraft.getInstance();
        if (FpvOverlay.fpvActive && droneUUID.equals(lastUuid)) {
            FpvOverlay.connectionLostTimer = 100;
            exitFpv(mc);
        }
    }

    private static void exitFpv(Minecraft mc) {
        if (!FpvOverlay.fpvActive) return;

        if (lastUuid != null) {
            ModNetwork.CHANNEL.sendToServer(new DroneControlPacket(
                    lastUuid, 0f, 0f, 0f, 0f,
                    mc.options != null ? mc.options.renderDistance().get() : 10
            ));
        }
        FpvOverlay.fpvActive = false;
        throttle = 0f;
        mouseInit = false;
        if (mc.level != null && lastViewRadius != 0) {
            mc.level.getChunkSource().updateViewRadius(mc.options.renderDistance().get());
        }
        lastViewRadius = 0;
        resetMouseKeys(mc);
        mc.tell(() -> {
            if (mc.player != null && mc.getCameraEntity() != mc.player) {
                mc.setCameraEntity(mc.player);
            }
        });
    }

    private static void resetMouseKeys(Minecraft mc) {
        mc.options.keyUse.setDown(false);
        mc.options.keyAttack.setDown(false);
        if (mc.player != null) {
            mc.player.swinging = false;
            mc.player.swingTime = 0;
        }
    }

    private static ItemStack getMainHandConnectedRemote(LocalPlayer player) {
        ItemStack stack = player.getMainHandItem();
        if (stack.getItem() == ModItems.REMOTE_CONNECTED.get() && stack.hasTag() && stack.getTag().hasUUID("DroneUUID")) return stack;
        return null;
    }

    private static ItemStack getConnectedRemote(LocalPlayer player) {
        ItemStack stack = player.getMainHandItem();
        if (stack.getItem() == ModItems.REMOTE_CONNECTED.get() && stack.hasTag() && stack.getTag().hasUUID("DroneUUID")) return stack;
        stack = player.getOffhandItem();
        if (stack.getItem() == ModItems.REMOTE_CONNECTED.get() && stack.hasTag() && stack.getTag().hasUUID("DroneUUID")) return stack;
        return null;
    }

    private static FpvDroneEntity findDrone(Minecraft mc, UUID uuid) {
        for (Entity e : mc.level.entitiesForRendering()) {
            if (e instanceof FpvDroneEntity d && d.getUUID().equals(uuid)) {
                return d;
            }
        }
        return null;
    }

    public static void resetThrottle() {
        throttle = 0f;
    }
}