package com.zzynes.flydrone.item;

import com.zzynes.flydrone.entity.FpvDroneEntity;
import com.zzynes.flydrone.DroneInputHandler;
import com.zzynes.flydrone.init.ModItems;
import net.minecraft.ChatFormatting;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;

import javax.annotation.Nullable;
import java.util.List;
import java.util.UUID;

public class DroneRemoteItem extends Item {

    private final boolean connected;

    public DroneRemoteItem(Properties properties, boolean connected) {
        super(properties);
        this.connected = connected;
    }

    @Override
    public InteractionResult interactLivingEntity(ItemStack stack, Player player, LivingEntity entity, InteractionHand hand) {
        if (entity instanceof FpvDroneEntity drone && !connected) {
            CompoundTag tag = stack.getOrCreateTag();
            tag.putUUID("DroneUUID", drone.getUUID());

            ItemStack newStack = new ItemStack(ModItems.REMOTE_CONNECTED.get());
            CompoundTag newTag = newStack.getOrCreateTag();
            newTag.putUUID("DroneUUID", drone.getUUID());
            player.setItemInHand(hand, newStack);

            player.displayClientMessage(Component.literal(ChatFormatting.GREEN + "Пульт подключён к дрону!"), true);
            return InteractionResult.SUCCESS;
        }
        return InteractionResult.PASS;
    }

    @Override
    public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand) {
        ItemStack stack = player.getItemInHand(hand);

        if (!connected) {
            player.displayClientMessage(Component.literal(ChatFormatting.RED + "Сначала привяжи пульт к дрону (ПКМ по дрону)"), true);
            return InteractionResultHolder.pass(stack);
        }

        CompoundTag tag = stack.getTag();
        if (tag != null && tag.hasUUID("DroneUUID")) {
            UUID droneUUID = tag.getUUID("DroneUUID");
            FpvDroneEntity drone = findDrone(level, player, droneUUID);

            if (drone == null) {
                disconnect(player, hand);
                return InteractionResultHolder.fail(stack);
            }

            player.displayClientMessage(Component.literal(ChatFormatting.YELLOW + "Сброс наряда невозможен — груз не установлен"), true);
            return InteractionResultHolder.success(stack);
        }

        return InteractionResultHolder.pass(stack);
    }

    @Override
    public void inventoryTick(ItemStack stack, Level level, Entity entity, int slot, boolean selected) {
        if (connected && entity instanceof Player player) {
            CompoundTag tag = stack.getTag();
            if (tag != null && tag.hasUUID("DroneUUID")) {
                UUID droneUUID = tag.getUUID("DroneUUID");
                FpvDroneEntity drone = findDrone(level, player, droneUUID);
                if (drone == null && selected) {
                    disconnect(player, player.getUsedItemHand());
                }
            }
        }
    }

    private void disconnect(Player player, InteractionHand hand) {
        DroneInputHandler.resetThrottle();
        player.setItemInHand(hand, new ItemStack(ModItems.REMOTE_DISCONNECTED.get()));
        player.displayClientMessage(Component.literal(ChatFormatting.RED + "Пульт отключён — дрон уничтожен"), true);
    }

    @Nullable
    private FpvDroneEntity findDrone(Level level, Player player, UUID uuid) {
        double range = 200.0;
        AABB area = new AABB(
                player.getX() - range, player.getY() - range, player.getZ() - range,
                player.getX() + range, player.getY() + range, player.getZ() + range
        );
        List<FpvDroneEntity> drones = level.getEntitiesOfClass(FpvDroneEntity.class, area);
        for (FpvDroneEntity drone : drones) {
            if (drone.getUUID().equals(uuid)) {
                return drone;
            }
        }
        return null;
    }

    @Override
    public void appendHoverText(ItemStack stack, @Nullable Level level, List<Component> tooltip, TooltipFlag flag) {
        if (stack.hasTag() && stack.getTag() != null && stack.getTag().hasUUID("DroneUUID")) {
            tooltip.add(Component.literal(ChatFormatting.GRAY + "Привязан к: " +
                    stack.getTag().getUUID("DroneUUID").toString().substring(0, 8) + "..."));
        }
    }
}