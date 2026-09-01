package com.zzynes.flydrone.DRONE;

import com.zzynes.flydrone.DRONE.entity.FpvDroneEntity;
import net.minecraft.client.Minecraft;
import net.minecraft.util.Mth;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.ViewportEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.joml.Quaternionf;

@Mod.EventBusSubscriber(modid = FlyDroneMod.MOD_ID, value = Dist.CLIENT)
public class FpvCameraHandler {

    @SubscribeEvent
    public static void onComputeCamera(ViewportEvent.ComputeCameraAngles event) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null) return;
        if (!(mc.getCameraEntity() instanceof FpvDroneEntity drone)) return;

        Quaternionf q = drone.getInterpolatedOrientation((float) event.getPartialTick());

        Vec3 f = rotate(q, 0f, 0f, 1f);
        Vec3 u = rotate(q, 0f, 1f, 0f);
        Vec3 r = rotate(q, 1f, 0f, 0f);

        float yaw = (float) Math.toDegrees(Math.atan2(-f.x, f.z));
        float pitch = (float) Math.toDegrees(-Math.asin(Mth.clamp(f.y, -1.0f, 1.0f)));
        float roll = (float) Math.toDegrees(Math.atan2(r.y, u.y));

        event.setYaw(yaw);
        event.setPitch(pitch);
        event.setRoll(roll);
    }

    private static Vec3 rotate(Quaternionf q, float x, float y, float z) {
        float qx = q.x, qy = q.y, qz = q.z, qw = q.w;
        float tx = 2 * (qy * z - qz * y);
        float ty = 2 * (qz * x - qx * z);
        float tz = 2 * (qx * y - qy * x);
        float rx = x + qw * tx + (qy * tz - qz * ty);
        float ry = y + qw * ty + (qz * tx - qx * tz);
        float rz = z + qw * tz + (qx * ty - qy * tx);
        return new Vec3(rx, ry, rz);
    }
}