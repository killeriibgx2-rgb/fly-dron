package com.zzynes.flydrone.mixin;

import com.zzynes.flydrone.entity.FpvDroneEntity;
import net.minecraft.server.level.ServerEntity;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.network.ServerPlayerConnection;
import net.minecraft.world.entity.Entity;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import java.util.Set;

@Mixin(targets = "net.minecraft.server.level.ChunkMap$TrackedEntity")
public class TrackedEntityMixin {

    @Shadow @Final private Entity entity;
    @Shadow @Final private ServerEntity serverEntity;
    @Shadow @Final private Set<ServerPlayerConnection> seenBy;

    @Inject(method = "updatePlayer", at = @At("HEAD"), cancellable = true)
    private void flydrone_forceTrackDrone(ServerPlayer player, CallbackInfo ci) {
        if (this.entity instanceof FpvDroneEntity drone) {
            if (drone.getControllerUUID() != null && drone.getControllerUUID().equals(player.getUUID())) {
                if (this.seenBy.add(player.connection)) {
                    this.serverEntity.addPairing(player);
                }
                ci.cancel();
            }
        }
    }
}