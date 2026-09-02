package com.zzynes.flydrone.mixin;

import com.zzynes.flydrone.entity.FpvDroneEntity;
import net.minecraft.core.SectionPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.item.ItemStack;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import java.util.UUID;

@Mixin(ServerPlayer.class)
public abstract class ServerPlayerMixin {

    @Shadow
    private void setLastSectionPos(SectionPos pos) {}

    @Inject(method = "tick", at = @At("HEAD"))
    private void flydrone_fakePlayerAtDrone(CallbackInfo ci) {
        ServerPlayer player = (ServerPlayer) (Object) this;
        FpvDroneEntity drone = flydrone_getDrone(player);
        if (drone != null) {
            this.setLastSectionPos(SectionPos.of(drone.blockPosition()));
        } else {
            this.setLastSectionPos(SectionPos.of(player));
        }
    }

    @Unique
    private static FpvDroneEntity flydrone_getDrone(ServerPlayer player) {
        if (player == null || !(player.level() instanceof ServerLevel sl)) return null;
        UUID droneUUID = flydrone_getDroneUUID(player);
        if (droneUUID == null) return null;
        for (Entity e : sl.getEntities().getAll()) {
            if (e instanceof FpvDroneEntity d && d.getUUID().equals(droneUUID)) {
                return d;
            }
        }
        return null;
    }

    @Unique
    private static UUID flydrone_getDroneUUID(ServerPlayer player) {
        ItemStack mainHand = player.getMainHandItem();
        CompoundTag mainTag = mainHand.getTag();
        if (mainTag != null && mainTag.contains("DroneUUID")) {
            return mainTag.getUUID("DroneUUID");
        }
        ItemStack offHand = player.getOffhandItem();
        CompoundTag offTag = offHand.getTag();
        if (offTag != null && offTag.contains("DroneUUID")) {
            return offTag.getUUID("DroneUUID");
        }
        return null;
    }
}