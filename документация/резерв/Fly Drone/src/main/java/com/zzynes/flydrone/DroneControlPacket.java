package com.zzynes.flydrone;

import com.zzynes.flydrone.entity.FpvDroneEntity;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.network.NetworkEvent;

import java.util.List;
import java.util.UUID;
import java.util.function.Supplier;

public class DroneControlPacket {
    private final UUID droneUUID;
    private final float throttle;
    private final float pitch;
    private final float roll;
    private final float yaw;
    private final int renderDistance;

    public DroneControlPacket(UUID droneUUID, float throttle, float pitch, float roll, float yaw, int renderDistance) {
        this.droneUUID = droneUUID;
        this.throttle = throttle;
        this.pitch = pitch;
        this.roll = roll;
        this.yaw = yaw;
        this.renderDistance = renderDistance;
    }

    public static void encode(DroneControlPacket packet, FriendlyByteBuf buf) {
        buf.writeUUID(packet.droneUUID);
        buf.writeFloat(packet.throttle);
        buf.writeFloat(packet.pitch);
        buf.writeFloat(packet.roll);
        buf.writeFloat(packet.yaw);
        buf.writeVarInt(packet.renderDistance);
    }

    public static DroneControlPacket decode(FriendlyByteBuf buf) {
        return new DroneControlPacket(
                buf.readUUID(),
                buf.readFloat(),
                buf.readFloat(),
                buf.readFloat(),
                buf.readFloat(),
                buf.readVarInt()
        );
    }

    public static void handle(DroneControlPacket packet, Supplier<NetworkEvent.Context> ctx) {
        ctx.get().enqueueWork(() -> {
            ServerPlayer player = ctx.get().getSender();
            if (player == null) return;

            double range = 2100.0;
            AABB area = new AABB(
                    player.getX() - range, player.getY() - range, player.getZ() - range,
                    player.getX() + range, player.getY() + range, player.getZ() + range
            );
            List<FpvDroneEntity> drones = player.level().getEntitiesOfClass(FpvDroneEntity.class, area);
            for (FpvDroneEntity drone : drones) {
                if (drone.getUUID().equals(packet.droneUUID)) {
                    drone.setController(player.getUUID());
                    drone.setRenderDistance(packet.renderDistance);
                    drone.setThrottle(packet.throttle);
                    drone.addPitchRate(packet.pitch);
                    drone.addRollRate(packet.roll);
                    drone.addYawRate(packet.yaw);
                    break;
                }
            }
        });
        ctx.get().setPacketHandled(true);
    }
}