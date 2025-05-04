import { Component, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatDrawerMode, MatSidenavModule } from '@angular/material/sidenav';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatBadgeModule } from '@angular/material/badge';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Document, SentinelService, User } from './sentinel.service';
import { Subject, delay, takeUntil } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { CommonModule } from '@angular/common';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { DocViewerComponent } from './doc-viewer/doc-viewer.component';

interface Message {
  id: number;
  text: string;
  sender: 'user' | 'assistant';
  date: Date;
}

@Component({
  selector: 'app-root',
  imports: [
    CommonModule,
    FormsModule,
    MatSidenavModule,
    MatIconModule,
    MatButtonModule,
    MatSelectModule,
    MatFormFieldModule,
    MatProgressSpinnerModule,
    MatBadgeModule,
    MatDialogModule,
  ],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class AppComponent implements OnInit {
  opened = true;
  mode: MatDrawerMode = 'side';
  documentCount = 0;
  documents: Document[] = [];
  loaded = false;
  users: User[] = [];
  userKey?: string;
  today = new Date();
  inputValue = '';
  messages: Message[] = [];
  $onDestroy = new Subject<void>();

  constructor(
    private sentinelService: SentinelService,
    private responsive: BreakpointObserver,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    // Setup breakpoint observer to detect if device is mobile
    this.responsive
      .observe([Breakpoints.Handset, Breakpoints.TabletLandscape])
      .pipe(takeUntil(this.$onDestroy), delay(1))
      .subscribe((result) => {
        // If it matches the breakpoints, display UI for mobile
        if (result.matches) {
          this.opened = false;
          this.mode = 'over';
        }
        // Otherwise, display UI for widescreen devices
        else {
          this.opened = true;
          this.mode = 'side';
        }
      });

    this.sentinelService.getUsers().subscribe((response) => {
      this.users = response.data;
      this.userKey = this.users.find((user) => user.role === 'user')?.key;

      this.loaded = true;
    });

    this.sentinelService
      .getUsers()
      .pipe(
        switchMap((response) => {
          this.users = response.data;
          this.userKey = this.users[0].key;
          return this.sentinelService.getDocuments(this.userKey);
        })
      )
      .subscribe({
        next: (response) => {
          this.documentCount = response.length;

          // Sort documents by sensitivity (low > medium > high)
          this.documents = response.sort((a, b) => {
            const sensitivityOrder: { [key: string]: number } = {
              low: 1,
              medium: 2,
              high: 3,
            };
            return (
              sensitivityOrder[a.sensitivity] - sensitivityOrder[b.sensitivity]
            );
          });
        },
        complete: () => {
          this.loaded = true;
        },
      });
  }

  toggleSidenav() {
    this.opened = !this.opened;
  }

  onUserChange(userKey: string) {
    this.sentinelService.getDocuments(userKey).subscribe((response) => {
      this.documentCount = response.length;

      // Sort documents by sensitivity (low > medium > high)
      this.documents = response.sort((a, b) => {
        const sensitivityOrder: { [key: string]: number } = {
          low: 1,
          medium: 2,
          high: 3,
        };
        return (
          sensitivityOrder[a.sensitivity] - sensitivityOrder[b.sensitivity]
        );
      });
    });
  }

  onSendMessage() {
    if (this.inputValue.trim() === '') {
      return;
    }

    const query = this.inputValue.trim();
    this.inputValue = '';

    this.messages.push({
      id: this.messages.length + 1,
      text: query,
      sender: 'user',
      date: new Date(),
    });

    this.sentinelService.query(this.userKey!, query).subscribe((response) => {
      this.messages.push({
        id: this.messages.length + 1,
        text: response.answer,
        sender: 'assistant',
        date: new Date(),
      });
    });
  }

  openDocument(document: Document) {
    const dialogRef = this.dialog.open(DocViewerComponent, {
      data: { document },
    });
  }
}
