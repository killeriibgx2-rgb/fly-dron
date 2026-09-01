package com.zzynes.flydrone.DRONE.item;

import com.zzynes.flydrone.DRONE.entity.FpvDroneEntity;
import com.zzynes.flydrone.DRONE.init.ModEntityTypes;
import net.minecraft.core.BlockPos;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.Level;

public class DroneSpawnItem extends Item {

    public DroneSpawnItem(Properties properties) {
        super(properties);
    }

    @Override
    public InteractionResult useOn(UseOnContext context) {
        Level level = context.getLevel();
        BlockPos pos = context.getClickedPos().above();
        Player player = context.getPlayer();

        if (!level.isClientSide()) {
            FpvDroneEntity drone = new FpvDroneEntity(ModEntityTypes.FPV_DRONE.get(), level);
            drone.setPos(pos.getX() + 0.5, pos.getY(), pos.getZ() + 0.5);
            level.addFreshEntity(drone);

            if (player != null && !player.isCreative()) {
                context.getItemInHand().shrink(1);
            }
        }

        return InteractionResult.sidedSuccess(level.isClientSide());
    }
}