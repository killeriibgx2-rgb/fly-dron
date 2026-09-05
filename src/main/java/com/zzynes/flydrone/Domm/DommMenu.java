package com.zzynes.flydrone.Domm;

import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.inventory.ContainerData;
import net.minecraft.world.inventory.ContainerLevelAccess;
import net.minecraft.world.inventory.SimpleContainerData;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraftforge.items.SlotItemHandler;

public class DommMenu extends AbstractContainerMenu {
    public final DommBlockEntity blockEntity;
    private final Level level;
    private final ContainerData dataAccess;

    public DommMenu(int containerId, Inventory inv, FriendlyByteBuf extraData) {
        this(containerId, inv, inv.player.level().getBlockEntity(extraData.readBlockPos()), new SimpleContainerData(2));
    }

    public DommMenu(int containerId, Inventory inv, BlockEntity entity, ContainerData dataAccess) {
        super(DommRegistry.DOMM_MENU.get(), containerId);
        checkContainerSize(inv, 4);
        this.blockEntity = (DommBlockEntity) entity;
        this.level = inv.player.level();
        this.dataAccess = dataAccess;
        addDataSlots(this.dataAccess);

        addPlayerInventory(inv);
        addPlayerHotbar(inv);

        this.addSlot(new SlotItemHandler(blockEntity.itemHandler, 0, 7, 3) {
            @Override
            public boolean mayPlace(ItemStack stack) {
                return stack.is(Items.COAL);
            }
        });
        this.addSlot(new SlotItemHandler(blockEntity.itemHandler, 1, 79, 16));
        this.addSlot(new SlotItemHandler(blockEntity.itemHandler, 2, 79, 46));
        this.addSlot(new SlotItemHandler(blockEntity.itemHandler, 3, 133, 60) {
            @Override
            public boolean mayPlace(ItemStack stack) {
                return false;
            }
        });
    }

    public int getCoalStored() {
        return this.dataAccess.get(0);
    }

    public int getTemperature() {
        return this.dataAccess.get(1);
    }

    private void addPlayerInventory(Inventory playerInventory) {
        for (int i = 0; i < 3; ++i) {
            for (int l = 0; l < 9; ++l) {
                this.addSlot(new Slot(playerInventory, l + i * 9 + 9, 8 + l * 18, 84 + i * 18));
            }
        }
    }

    private void addPlayerHotbar(Inventory playerInventory) {
        for (int i = 0; i < 9; ++i) {
            this.addSlot(new Slot(playerInventory, i, 8 + i * 18, 142));
        }
    }

    @Override
    public boolean stillValid(Player player) {
        return stillValid(ContainerLevelAccess.create(level, blockEntity.getBlockPos()), player, DommRegistry.DOMM_INTERFACE.get());
    }

    @Override
    public ItemStack quickMoveStack(Player playerIn, int index) {
        return ItemStack.EMPTY;
    }
}